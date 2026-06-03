"""
Metadata Analyzer Agent - Hybrid keyword+LLM topic detection

Two-layer approach:
  1. Keywords (fast path)  – covers common explicit topics
  2. LLM fallback (slow path) – handles anything else, open-ended
"""
import json
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MetadataAnalyzer:
    """Hybrid Keywords + LLM topic detection for academic content"""

    # ---------------------------------------------------------------------------
    # Language detection helpers
    # ---------------------------------------------------------------------------

    # Spanish function words that almost never appear in English text
    _ES_FUNCTION_WORDS: frozenset = frozenset({
        "de", "la", "el", "en", "que", "los", "las", "con", "por", "para",
        "una", "del", "se", "es", "son", "está", "pero", "como", "más", "al",
        "sus", "su", "hay", "también", "este", "esta", "estos", "estas",
        "entre", "sobre", "cuando", "muy", "ya", "así", "sino", "hasta",
        "desde", "hacia", "durante", "mediante", "según", "porque", "aunque",
        "donde", "cual", "cuyo", "cuya", "mismo", "misma",
    })

    # English function words that almost never appear in Spanish text
    _EN_FUNCTION_WORDS: frozenset = frozenset({
        "the", "and", "for", "with", "this", "that", "are", "have", "from",
        "they", "was", "will", "can", "has", "been", "more", "than", "when",
        "all", "its", "not", "but", "which", "their", "these", "those", "also",
        "were", "about", "into", "would", "could", "should", "through",
        "during", "before", "after", "between", "under", "such", "other",
    })

    # English-only keywords that are ALSO common Spanish words → skip these
    # when the detected language is Spanish to prevent false positives.
    #
    #   "verse"  – Spanish reflexive verb "verse" (to be seen / to find oneself)
    #              e.g. "podía verse a simple vista" = "could be seen with the naked eye"
    #   "base"   – Spanish noun/adjective (base, basis, foundation)
    #              e.g. "la base del conocimiento", "en base a", "base de datos"
    #   "mine"   – Spanish possessive "mío/mía" rarely spelled "mine", but
    #              "mina" (mine the place) can create ambiguity in geology texts
    #   "current"– Spanish noun "corriente" (current, stream, flow)
    #   "plot"   – Spanish "trama/complot" — rarely "plot" but possible in
    #              translated academic content
    #   "theme"  – Spanish "tema" — different word, but "theme" can appear as
    #              a loanword in modern Spanish writing
    _SPANISH_AMBIGUOUS_EN_KEYWORDS: frozenset = frozenset({
        "verse", "base", "mine", "current", "plot", "theme",
    })

    @staticmethod
    def _detect_language(text: str) -> str:
        """
        Detect the primary language of a text sample.

        Algorithm (no external libraries needed):

          Tier 1 — hard character signals (single match is conclusive):
            • ñ, ¿, ¡ → Spanish (essentially unique to Spanish)

          Tier 2 — accent count (reliable for medium/long texts):
            • 4+ accented Spanish vowels (á é í ó ú ü) in first 500 chars → "es"
              (French/Portuguese prefer different accent patterns)

          Tier 3 — function-word frequency (reliable for any length ≥ ~50 words):
            • Compare word overlap against curated ES / EN sets
            • Threshold: 2 matching function words gives a decision

          Tier 4 — secondary Romance characters → "pt" or "fr"

          Unknown → "unknown" (caller treats it as neutral)

        Returns: "es" | "en" | "pt" | "fr" | "unknown"
        """
        sample = text[:3000]
        sample_lower = sample.lower()

        # ── Tier 1: hard character signals ───────────────────────────────────
        if re.search(r"[ñ¿¡]", sample):
            return "es"

        # ── Tier 2: accented Spanish vowels in a short window ────────────────
        # 4+ in the first 500 chars means the text is almost certainly Spanish
        # (á, é, í, ó, ú, ü are all standard Spanish, rare in English).
        early_accents = len(re.findall(r"[áéíóúü]", sample_lower[:500]))
        if early_accents >= 4:
            return "es"

        # ── Tier 3: function-word frequency ──────────────────────────────────
        words = set(re.findall(r"\b[a-záéíóúüàâæœùûÿãõçèêë]+\b", sample_lower))

        es_score = len(words & MetadataAnalyzer._ES_FUNCTION_WORDS)
        en_score = len(words & MetadataAnalyzer._EN_FUNCTION_WORDS)

        # Remaining accented vowels in full sample add to ES score
        es_accents = len(re.findall(r"[áéíóúü]", sample_lower))
        es_score += es_accents // 3     # 3 accents → +1 point

        if es_score >= 2 and es_score > en_score:
            return "es"
        if en_score >= 2 and en_score > es_score:
            return "en"

        # ── Tier 4: secondary Romance signals ────────────────────────────────
        if re.search(r"[ãõ]", sample):
            return "pt"
        if re.search(r"[àâæœùûÿèê]", sample):
            return "fr"

        return "unknown"

    # ---------------------------------------------------------------------------
    # Keyword database – subject → topic → trigger words
    # ---------------------------------------------------------------------------
    KEYWORD_DATABASE: Dict[str, Dict[str, list]] = {
        "Biology": {
            "Photosynthesis": ["photosynthesis", "chlorophyll", "light reaction", "chloroplast", "calvin cycle"],
            "Cell Cycle": ["cell cycle", "mitosis", "cytokinesis", "meiosis", "cell division"],
            "Mitochondria": ["mitochondria", "atp", "oxidative phosphorylation", "cellular respiration", "krebs cycle"],
            "Genetics": ["genetics", "dna", "rna", "gene", "chromosome", "mutation", "allele", "genotype", "phenotype"],
            "Evolution": ["evolution", "natural selection", "darwin", "species", "adaptation", "fossil"],
            "Ecology": ["ecology", "ecosystem", "food chain", "biome", "biodiversity", "habitat", "population"],
            "Cell Biology": ["cell", "membrane", "nucleus", "organelle", "eukaryote", "prokaryote", "ribosome"],
            "Reproduction": ["reproduction", "sexual reproduction", "asexual", "fertilization", "embryo", "gamete"],
            "Nervous System": ["neuron", "nervous system", "synapse", "brain", "action potential", "neurotransmitter"],
        },
        "Chemistry": {
            "Atomic Structure": ["atom", "electron", "proton", "neutron", "orbital", "atomic number", "periodic table"],
            "Chemical Bonding": ["chemical bond", "ionic bond", "covalent bond", "electronegativity", "valence"],
            "Thermodynamics": ["enthalpy", "entropy", "gibbs free energy", "thermodynamics", "exothermic", "endothermic"],
            "Acids and Bases": ["acid", "base", "ph", "buffer", "neutralization", "titration", "hydroxide"],
            "Organic Chemistry": ["organic chemistry", "carbon", "hydrocarbon", "alkane", "alkene", "functional group"],
            "Electrochemistry": ["electrochemistry", "electrolysis", "oxidation", "reduction", "redox", "electrode"],
            "Stoichiometry": ["stoichiometry", "mole", "molar mass", "reactant", "product", "limiting reagent"],
        },
        "Physics": {
            "Mechanics": ["force", "velocity", "acceleration", "momentum", "newton", "gravity", "friction", "kinematics"],
            "Thermodynamics": ["heat", "temperature", "thermal equilibrium", "specific heat", "ideal gas"],
            "Electromagnetism": ["electric field", "magnetic field", "charge", "current", "voltage", "resistance", "capacitor"],
            "Waves and Optics": ["wave", "frequency", "wavelength", "diffraction", "refraction", "reflection", "optics"],
            "Quantum Physics": ["quantum", "photon", "uncertainty principle", "wave-particle duality", "schrodinger"],
            "Relativity": ["relativity", "einstein", "spacetime", "time dilation", "lorentz", "speed of light"],
            "Nuclear Physics": ["nuclear", "radioactive", "decay", "fission", "fusion", "half-life"],
        },
        "Mathematics": {
            "Calculus": ["calculus", "derivative", "integral", "limit", "differential equation", "gradient"],
            "Algebra": ["algebra", "equation", "polynomial", "quadratic", "linear equation", "matrix", "vector"],
            "Geometry": ["geometry", "triangle", "angle", "circle", "perimeter", "area", "volume", "polygon"],
            "Statistics": ["statistics", "probability", "mean", "median", "standard deviation", "distribution", "variance"],
            "Trigonometry": ["trigonometry", "sine", "cosine", "tangent", "radian", "pythagorean"],
            "Number Theory": ["prime number", "divisibility", "number theory", "modular arithmetic"],
        },
        "History": {
            "French Revolution": ["french revolution", "guillotine", "napoleon", "bastille", "robespierre", "jacobins"],
            "World War 2": ["world war 2", "world war ii", "wwii", "nazi", "holocaust", "d-day", "hiroshima"],
            "World War 1": ["world war 1", "world war i", "wwi", "trench warfare", "armistice", "versailles"],
            "Ancient Rome": ["roman empire", "julius caesar", "rome", "senate", "gladiator", "colosseum"],
            "Ancient Greece": ["ancient greece", "polis", "athens", "sparta", "democracy", "olympics"],
            "Renaissance": ["renaissance", "humanism", "michelangelo", "leonardo da vinci", "reformation"],
            "Cold War": ["cold war", "ussr", "nato", "nuclear arms race", "iron curtain", "cuban missile"],
            "Industrial Revolution": ["industrial revolution", "steam engine", "factory", "urbanization", "capitalism"],
        },
        "Literature": {
            "Shakespeare": ["shakespeare", "hamlet", "romeo and juliet", "macbeth", "othello", "sonnets"],
            # "verse" removed — it is a common Spanish reflexive verb ("podía verse" = "could be seen")
            # and causes false positives on science/astronomy texts written in Spanish.
            "Poetry": ["poetry", "poem", "rhyme", "in verse", "metaphor", "simile", "stanza",
                       "poesía", "poema", "rima", "estrofa"],
            "Narrative": ["narrative", "plot", "character", "setting", "theme", "protagonist", "antagonist"],
            "Modern Literature": ["modern literature", "modernism", "postmodernism", "stream of consciousness"],
        },
        # ── Astronomy & Space Sciences ─────────────────────────────────────────
        "Astronomy": {
            "General Astronomy": [
                # English
                "astronomy", "astrophysics", "astronomer", "telescope", "celestial",
                "cosmos", "universe", "galaxy", "galaxies", "star", "stars", "planet",
                "planets", "solar system", "comet", "asteroid", "nebula", "supernova",
                "black hole", "orbit", "orbital", "space", "spacecraft", "satellite",
                "light-year", "milky way", "big bang", "exoplanet", "constellation",
                "interstellar", "dark matter", "dark energy", "quasar", "pulsar",
                "neutron star", "cosmology", "astrobiology",
                # Spanish
                "astronomía", "astrofísica", "astrónomo", "astrónomos", "telescopio",
                "telescopios", "celeste", "celestes", "cosmos", "universo",
                "galaxia", "galaxias", "estrella", "estrellas", "planeta", "planetas",
                "sistema solar", "cometa", "asteroide", "nebulosa", "supernova",
                "agujero negro", "órbita", "orbital", "espacio", "satélite", "cuerpo celeste",
                "cuerpos celestes", "año luz", "vía láctea", "big bang", "exoplaneta",
                "constelación", "constelaciones", "interestelar", "materia oscura",
                "energía oscura", "quásar", "púlsar", "cosmología", "astrobiología",
                "astros", "astro", "radiotelescopio", "sonda espacial",
            ],
            "Observational Astronomy": [
                "observation", "observational", "imaging", "spectroscopy", "photometry",
                "radio telescope", "infrared", "ultraviolet", "x-ray astronomy",
                "hubble", "james webb", "alma observatory",
                "observación", "observacional", "espectroscopía", "fotometría",
                "infrarrojo", "rayos x", "microondas",
            ],
            "Cosmology": [
                "cosmology", "big bang theory", "cosmic microwave", "inflation",
                "dark matter", "dark energy", "expansion of universe",
                "cosmología", "teoría del big bang", "expansión del universo",
            ],
            "Astrobiology": [
                "astrobiology", "extraterrestrial life", "biosignature", "habitable zone",
                "astrobiología", "vida extraterrestre", "zona habitable", "exoplaneta habitable",
            ],
        },
        "Geography": {
            "Physical Geography": ["continent", "ocean", "mountain", "river", "climate zone", "erosion", "tectonic"],
            "Human Geography": ["urbanization", "migration", "culture", "demography"],
            "Cartography": ["map", "projection", "latitude", "longitude", "coordinate", "cartography"],
        },
        "Economics": {
            "Microeconomics": ["supply", "demand", "price elasticity", "market equilibrium", "monopoly", "consumer surplus"],
            "Macroeconomics": ["gdp", "inflation", "unemployment", "fiscal policy", "monetary policy", "recession"],
            "International Trade": ["export", "import", "tariff", "comparative advantage", "globalization"],
        },
        # ── Technology / Computer Science ──────────────────────────────────────
        "Computer Science": {
            "Programming": ["programming", "coding", "algorithm", "function", "variable", "loop", "syntax", "debug", "código", "programar"],
            "DevOps": ["devops", "ci/cd", "pipeline", "docker", "kubernetes", "helm", "deployment", "infrastructure as code", "terraform", "ansible", "jenkins", "github actions", "gitlab ci", "continuous integration", "continuous delivery", "container", "contenedor"],
            "Web Development": ["html", "css", "javascript", "typescript", "react", "vue", "angular", "frontend", "backend", "web development", "rest api", "graphql", "node", "django", "flask", "fastapi", "next.js"],
            "Databases": ["database", "sql", "nosql", "query", "mongodb", "postgresql", "mysql", "sqlite", "schema", "orm", "index", "base de datos"],
            "Artificial Intelligence": ["machine learning", "neural network", "deep learning", "nlp", "artificial intelligence", "ai model", "training data", "inteligencia artificial", "aprendizaje automático"],
            "Networking": ["networking", "tcp/ip", "dns", "http", "https", "protocol", "firewall", "router", "bandwidth", "vpn", "proxy", "red"],
            "Cybersecurity": ["cybersecurity", "security", "encryption", "vulnerability", "penetration testing", "malware", "authentication", "authorization", "hacking", "seguridad informática"],
            "Data Science": ["data science", "pandas", "numpy", "visualization", "regression", "clustering", "dataset", "ciencia de datos", "análisis de datos"],
            "Cloud Computing": ["cloud", "aws", "azure", "gcp", "google cloud", "serverless", "microservices", "cloud computing", "nube", "s3", "lambda", "ec2"],
            "Software Engineering": ["software engineering", "design pattern", "oop", "agile", "scrum", "sprint", "software architecture", "solid principles", "clean code", "refactoring", "unit test"],
            "Operating Systems": ["operating system", "linux", "unix", "windows", "kernel", "process", "thread", "file system", "shell", "bash", "terminal", "sistema operativo"],
            "Version Control": ["git", "github", "gitlab", "version control", "branch", "commit", "merge", "pull request", "repository"],
        },
        # ── Earth Sciences / Geohazards ────────────────────────────────────────
        "Earth Sciences": {
            "Geohazards": [
                "geoamenaza", "amenaza natural", "natural hazard",
                "sismo", "terremoto", "earthquake",
                "volcán", "volcan", "volcano", "eruption", "erupción",
                "lahar", "landslide", "deslizamiento",
                "desastre natural", "natural disaster",   # multi-word → no false positives
                "riesgo sísmico", "riesgo volcánico",     # require geohazard qualifier
                "riesgo geológico", "geological risk",
                "vulnerabilidad sísmica", "seismic vulnerability",
                "vulnerability", "sendai",
                # NOTE: bare "riesgo" and bare "risk" intentionally removed —
                # they are common everyday words in Spanish that cause false
                # positives in news articles, election coverage, etc.
            ],
            "Seismology": ["seismic", "richter", "fault", "tectonic plate", "epicenter", "seismograph", "magnitud sísmica"],
            "Geology": [
                # English
                "geology", "rock", "mineral", "minerals", "stratigraphy", "sediment", "magma",
                "lava", "lithosphere", "ore", "mining", "mine", "quarry", "crystalline",
                "igneous", "metamorphic", "sedimentary", "geochemistry",
                # Spanish – geology & raw materials (the most common mismatch)
                "geología", "geociencias", "roca", "rocas", "mineral", "minerales",
                "yacimiento", "yacimientos", "estrato", "estratigrafía", "litosfera",
                "corteza terrestre", "geoquímica", "minería", "minero", "metalurgia",
                "metalúrgico", "metal", "metales",
            ],
            "Georesources": [
                # This topic is designed to win over Chemistry for raw-materials documents
                "georrecurso", "georrecursos", "materia prima", "materias primas",
                "recurso mineral", "recursos minerales", "raw material", "raw materials",
                "mineral resource", "mineral resources", "natural resource", "recursos naturales",
                "recurso natural", "geomaterial", "geomateriales",
            ],
            "Critical Minerals": [
                "mineral crítico", "minerales críticos", "critical mineral", "critical minerals",
                "tierra rara", "tierras raras", "rare earth", "rare earth elements", "ree",
                "litio", "lithium", "cobalto", "cobalt", "níquel", "nickel",
                "cobre", "copper", "hierro", "gold", "plata", "silver", "zinc",
                "estaño", "tin", "bronce", "bronze", "bauxita", "bauxite",
                "grafito", "graphite", "titanio", "titanium", "tungsteno", "tungsten",
                "neodimio", "neodymium", "disprosio", "dysprosium", "galio", "gallium",
                "germanio", "germanium", "escandio", "scandium", "lantánido",
                "semiconductor", "semiconductores",
            ],
            "Historical Geology": [
                "paleolítico", "paleolithic", "edad de piedra", "stone age",
                "edad de bronce", "bronze age", "edad del hierro", "iron age",
                "edad de los metales", "age of metals", "edad media", "middle ages",
                "edad moderna", "modern era", "era geológica", "geological age",
                "cazadores-recolectores", "hunter-gatherers",
            ],
            "Climatology": ["climate", "weather", "precipitation", "hurricane", "huracán", "tropical storm", "el niño", "la niña", "drought", "sequía"],
            "Oceanography": ["ocean", "tsunami", "sea level", "coral reef", "marine", "current", "océano"],
        },
        # ── Business & Management ──────────────────────────────────────────────
        "Business": {
            "Management": ["management", "leadership", "strategy", "organizational", "human resources", "gestión", "liderazgo"],
            "Marketing": ["marketing", "branding", "advertising", "market research", "consumer behavior", "social media marketing"],
            "Finance": ["finance", "investment", "portfolio", "stock", "bond", "budget", "financial statement", "finanzas"],
            "Entrepreneurship": ["startup", "entrepreneurship", "venture capital", "business model", "pitch", "emprendimiento"],
            "Project Management": ["project management", "gantt", "stakeholder", "deliverable", "milestone", "pmp", "waterfall", "agile project"],
        },
        # ── Philosophy & Social Sciences ──────────────────────────────────────
        "Philosophy": {
            "Ethics": ["ethics", "morality", "moral philosophy", "deontology", "utilitarianism", "virtue ethics", "ética"],
            "Epistemology": ["epistemology", "knowledge", "truth", "belief", "justified", "rationalism", "empiricism"],
            "Logic": ["logic", "argument", "fallacy", "syllogism", "deduction", "induction", "lógica"],
        },
        "Social Sciences": {
            "Psychology": ["psychology", "behavior", "cognitive", "therapy", "mental health", "freud", "piaget", "psicología"],
            "Sociology": ["sociology", "society", "social class", "culture", "norms", "institutions", "sociología"],
            "Political Science": [
                # English
                "politics", "political", "government", "democracy", "policy",
                "constitution", "political party", "election", "elections",
                "electoral", "voter", "voters", "ballot", "candidate", "campaign",
                "president", "congress", "senate", "parliament", "legislation",
                "voting", "referendum", "polling", "debate",
                # Spanish – essential for Latin American news
                "ciencia política", "elección", "elecciones", "electoral",
                "proceso electoral", "votantes", "voto", "votar", "votación",
                "candidato", "candidatos", "candidatura", "partido político",
                "partidos políticos", "gobierno", "democracia", "constitución",
                "presidente", "presidencial", "congreso", "senado", "parlamento",
                "legislación", "campaña electoral", "resultados electorales",
                "registrador", "registraduría", "padrón electoral",
                "comicios", "sufragio", "electorado", "electo",
            ],
        },
        # ── Language & Communication ───────────────────────────────────────────
        "Language": {
            "Spanish": ["gramática española", "conjugación", "español", "sintaxis española", "ortografía", "lengua castellana"],
            "English": ["grammar", "english language", "vocabulary", "writing skills", "comprehension", "tense"],
            "Linguistics": ["linguistics", "phonology", "morphology", "syntax", "semantics", "pragmatics"],
        },
    }

    CONTENT_TYPE_KEYWORDS: Dict[str, list] = {
        "exam": ["exam", "test", "quiz", "questions", "assessment", "multiple choice", "examen", "evaluación", "prueba"],
        "guide": ["guide", "tutorial", "how-to", "manual", "study guide", "guía", "introduction to", "introducción", "overview", "beginners guide", "learn", "aprende", "explica cómo"],
        "slideshow": ["slides", "presentation", "powerpoint", "slideshow", "diapositivas", "presentación"],
        "question": ["create questions", "generate questions", "preguntas", "list questions", "ejercicios"],
        "text": ["write", "explain", "describe", "summarize", "summarise", "essay", "article", "explica", "describe", "resume"],
    }

    # ---------------------------------------------------------------------------
    # Public API  (now async so we can call _llm_detect directly)
    # ---------------------------------------------------------------------------

    @staticmethod
    async def hybrid_detect(
        text: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        corrections: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Async hybrid detection: language → keywords → LLM fallback.

        Args:
            text: The user prompt or document text to classify.
            document_metadata: Optional metadata extracted from an uploaded document
                (overrides detected subject/topic when present).
            corrections: Optional list of recent user-supplied classification
                corrections, each a dict with keys
                ``sample``, ``original_subject``, ``corrected_subject``.
                These are injected as few-shot examples into the LLM prompt so the
                model learns from past mistakes without retraining.

        Returns:
            {
                "subject": str | None,
                "topic": str | None,
                "content_type": str | None,
                "confidence": float,
                "method": "keywords" | "llm" | "document",
                "language": "es" | "en" | "pt" | "fr" | "unknown"
            }
        """
        # Detect language first — used by keyword scorer to skip cross-language
        # false positives (e.g. Spanish "verse" ≠ English "verse" in poetry).
        language = MetadataAnalyzer._detect_language(text)
        logger.debug("Detected language: %s (sample length %d)", language, len(text))

        result: Dict[str, Any] = {
            "subject": None,
            "topic": None,
            "content_type": None,
            "confidence": 0.0,
            "method": None,
            "language": language,
        }

        # Layer 1: keyword detection (fast path, language-aware)
        kw_result = MetadataAnalyzer._keywords_detect(text, language=language)

        if kw_result["confidence"] >= 0.75:
            result.update(kw_result)
            result["method"] = "keywords"
            result["language"] = language   # _keywords_detect doesn't return language
        else:
            # Layer 2: LLM detection — open-ended, handles any topic/language.
            # Pass user corrections so the LLM can learn from past mistakes.
            try:
                llm_result = await MetadataAnalyzer._llm_detect(
                    text, language=language, corrections=corrections
                )
                if llm_result.get("confidence", 0.0) > 0:
                    result.update(llm_result)
                    result["method"] = "llm"
                    result["language"] = language
                else:
                    result.update(kw_result)
                    result["method"] = "keywords"
                    result["language"] = language
            except Exception as exc:
                logger.warning("LLM topic detection failed, using keyword result: %s", exc)
                result.update(kw_result)
                result["method"] = "keywords"
                result["language"] = language

        # Merge with document metadata (document signals take precedence)
        if document_metadata:
            if document_metadata.get("subject"):
                result["subject"] = document_metadata["subject"]
                result["method"] = "document"
            if document_metadata.get("topic"):
                result["topic"] = document_metadata["topic"]
                result["method"] = "document"
            # Prefer document language if provided (e.g. set during ingest)
            if document_metadata.get("language"):
                result["language"] = document_metadata["language"]

        logger.info(
            "Detection result — subject=%r topic=%r lang=%r confidence=%.2f method=%s",
            result["subject"], result["topic"], result["language"],
            result["confidence"], result["method"],
        )
        return result

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _word_in_text(keyword: str, text_lower: str) -> bool:
        """Word-boundary aware keyword match."""
        if " " in keyword or "/" in keyword:
            return keyword in text_lower
        return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text_lower))

    @staticmethod
    def _keywords_detect(text: str, language: str = "unknown") -> Dict[str, Any]:
        """
        Fast keyword-based detection, language-aware.

        When `language` is "es" (Spanish), English keywords that are also
        common Spanish words (_SPANISH_AMBIGUOUS_EN_KEYWORDS) are skipped to
        prevent false positives such as:
          • "verse"   → Spanish reflexive verb (podía verse a simple vista)
          • "base"    → Spanish noun (base del conocimiento, base de datos)
          • "current" → Spanish noun (corriente)
        """
        text_lower = text.lower()
        skip_in_spanish = (
            MetadataAnalyzer._SPANISH_AMBIGUOUS_EN_KEYWORDS
            if language == "es"
            else frozenset()
        )

        best: Dict[str, Any] = {
            "subject": None,
            "topic": None,
            "content_type": None,
            "confidence": 0.0,
        }

        # Content-type detection
        for ctype, keywords in MetadataAnalyzer.CONTENT_TYPE_KEYWORDS.items():
            if any(MetadataAnalyzer._word_in_text(kw, text_lower) for kw in keywords):
                best["content_type"] = ctype
                break

        # Subject + topic detection
        for subject, topics in MetadataAnalyzer.KEYWORD_DATABASE.items():
            for topic, keywords in topics.items():
                match_count = sum(
                    1
                    for kw in keywords
                    if kw not in skip_in_spanish          # skip ambiguous ES/EN words
                    and MetadataAnalyzer._word_in_text(kw, text_lower)
                )
                if match_count > 0:
                    confidence = min(0.95, 0.75 + (match_count - 1) * 0.1)
                    if confidence > best["confidence"]:
                        best["subject"] = subject
                        best["topic"] = topic
                        best["confidence"] = confidence

        return best

    @staticmethod
    async def _llm_detect(
        text: str,
        language: str = "unknown",
        corrections: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        LLM-based detection for any topic, fully open-ended.
        The subject can be ANY academic or professional field.

        ``corrections`` is a list of dicts each with keys
        ``sample``, ``original_subject``, ``corrected_subject``.
        When present they are formatted as few-shot examples in the prompt so the
        model learns from the user's past manual corrections without retraining.
        """
        try:
            from app.services.llm_service import LLMService
            from app.core.config import settings
            # NOTE: do NOT import google.generativeai here — the container uses
            # the newer google.genai SDK.  LLMService._get_client() already
            # returns the correct client; we just use it directly.

            client = LLMService._get_client()

            lang_hint = ""
            if language == "es":
                lang_hint = "The text is written in Spanish. "
            elif language == "pt":
                lang_hint = "The text is written in Portuguese. "
            elif language == "fr":
                lang_hint = "The text is written in French. "

            # Build few-shot block from user's past corrections
            corrections_block = ""
            if corrections:
                valid = [
                    c for c in corrections
                    if c.get("corrected_subject") and c.get("sample")
                ][:8]   # cap at 8 examples to stay within token budget
                if valid:
                    corrections_block = (
                        "\nThis user has corrected past misclassifications. "
                        "Learn from these and apply the same logic to new text:\n"
                    )
                    for c in valid:
                        sample = c["sample"][:80].replace('"', "'")
                        orig = c.get("original_subject") or "unknown"
                        corr = c["corrected_subject"]
                        corrections_block += (
                            f'- Text like "{sample}" → '
                            f'correct subject is "{corr}" (not "{orig}")\n'
                        )
                    corrections_block += "\n"

            prompt = (
                "You are a topic classifier. Analyze the following text and identify:\n"
                "1. subject: the academic or professional field (e.g. Computer Science, Biology, History, Mathematics, "
                "DevOps, Marketing, Philosophy, Physics, Earth Sciences, Astronomy, Economics, Language, etc. — be specific, "
                "use English)\n"
                "2. topic: the specific sub-topic within that field (e.g. Docker & Kubernetes, Photosynthesis, "
                "French Revolution, Calculus, Geohazards, General Astronomy — be specific, use English)\n"
                "3. content_type: one of exam | guide | slideshow | question | text\n\n"
                f"{lang_hint}"
                f"{corrections_block}"
                "Rules:\n"
                "- Always respond in English for subject and topic, regardless of the text's language.\n"
                "- Do NOT restrict subject to any fixed list — infer freely.\n"
                "- Return ONLY valid JSON, nothing else.\n\n"
                f'Text: "{text[:500]}"\n\n'
                'JSON format: {"subject": "...", "topic": "...", "content_type": "..."}'
            )

            response = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
            )

            raw = response.text.strip()
            json_start = raw.find("{")
            json_end = raw.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(raw[json_start:json_end])
                subject = parsed.get("subject") or None
                topic = parsed.get("topic") or None
                content_type = parsed.get("content_type") or None
                if subject and topic:
                    logger.info("LLM detected: subject=%r topic=%r content_type=%r", subject, topic, content_type)
                    return {
                        "subject": subject,
                        "topic": topic,
                        "content_type": content_type,
                        "confidence": 0.85,
                    }
        except Exception as exc:
            logger.warning("LLM metadata extraction error: %s", exc)

        return {
            "subject": None,
            "topic": None,
            "content_type": None,
            "confidence": 0.0,
        }
