"""
Metadata Analyzer Agent - Hybrid keyword+LLM topic detection

Implements a two-layer approach:
  1. Keywords (fast path)  – covers ~95% of explicit topics
  2. LLM fallback (slow path) – handles implicit / nuanced topics
"""
import json
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MetadataAnalyzer:
    """Hybrid Keywords + LLM topic detection for academic content"""

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
            "Osmotic Pressure": ["osmotic pressure", "osmosis", "semipermeable membrane", "solute", "solvent", "osmolarity"],
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
            "Trigonometry": ["trigonometry", "sine", "cosine", "tangent", "angle", "radian", "pythagorean"],
            "Number Theory": ["prime number", "divisibility", "number theory", "modular arithmetic", "integer"],
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
            "Poetry": ["poetry", "poem", "rhyme", "verse", "metaphor", "simile", "stanza"],
            "Narrative": ["narrative", "plot", "character", "setting", "theme", "protagonist", "antagonist"],
            "Modern Literature": ["modern literature", "modernism", "postmodernism", "stream of consciousness"],
        },
        "Geography": {
            "Physical Geography": ["continent", "ocean", "mountain", "river", "climate zone", "erosion", "tectonic"],
            "Human Geography": ["population", "urbanization", "migration", "culture", "demography"],
            "Cartography": ["map", "projection", "latitude", "longitude", "coordinate", "cartography"],
        },
        "Economics": {
            "Microeconomics": ["supply", "demand", "price elasticity", "market equilibrium", "monopoly", "consumer surplus"],
            "Macroeconomics": ["gdp", "inflation", "unemployment", "fiscal policy", "monetary policy", "recession"],
            "International Trade": ["trade", "export", "import", "tariff", "comparative advantage", "globalization"],
        },
    }

    CONTENT_TYPE_KEYWORDS: Dict[str, list] = {
        "exam": ["exam", "test", "quiz", "questions", "assessment", "multiple choice", "examen"],
        "guide": ["guide", "tutorial", "how-to", "manual", "study guide", "guía", "learning guide"],
        "slideshow": ["slides", "presentation", "powerpoint", "slideshow", "diapositivas"],
        "question": ["create questions", "generate questions", "preguntas", "list questions"],
        "text": ["write", "explain", "describe", "summarize", "summarise", "essay", "article"],
    }

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    @staticmethod
    def hybrid_detect(
        text: str,
        document_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Hybrid detection: keywords first, then LLM if confidence is low.

        Returns:
            {
                "subject": str | None,
                "topic": str | None,
                "content_type": str | None,
                "confidence": float,
                "method": "keywords" | "llm" | "document"
            }
        """
        result: Dict[str, Any] = {
            "subject": None,
            "topic": None,
            "content_type": None,
            "confidence": 0.0,
            "method": None,
        }

        # Layer 1: keyword detection (fast path)
        kw_result = MetadataAnalyzer._keywords_detect(text)

        if kw_result["confidence"] >= 0.75:
            result.update(kw_result)
            result["method"] = "keywords"
        else:
            # Layer 2: LLM detection (slow path) – only when keywords are uncertain.
            # We run this in a thread pool when an event loop is already running so
            # that we don't block FastAPI's event loop.
            try:
                import asyncio
                import concurrent.futures

                try:
                    # Try to get the running loop (inside FastAPI / async context)
                    asyncio.get_running_loop()
                    # Run in a separate thread that creates its own event loop
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(
                            asyncio.run, MetadataAnalyzer._llm_detect(text)
                        )
                        llm_result = future.result(timeout=30)
                except RuntimeError:
                    # No running loop – call directly
                    llm_result = asyncio.run(MetadataAnalyzer._llm_detect(text))

                if llm_result.get("confidence", 0.0) > 0:
                    result.update(llm_result)
                    result["method"] = "llm"
                else:
                    # LLM also gave up – return whatever keywords found
                    result.update(kw_result)
                    result["method"] = "keywords"
            except Exception as exc:
                logger.warning("LLM topic detection failed, falling back to keyword result: %s", exc)
                result.update(kw_result)
                result["method"] = "keywords"

        # Merge with document metadata (document signals take precedence for subject/topic)
        if document_metadata:
            if document_metadata.get("subject"):
                result["subject"] = document_metadata["subject"]
                result["method"] = "document"
            if document_metadata.get("topic"):
                result["topic"] = document_metadata["topic"]
                result["method"] = "document"

        return result

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _word_in_text(keyword: str, text_lower: str) -> bool:
        """Check if a keyword appears in text with word-boundary semantics.

        Single words are checked as whole-words (so 'evolution' does not match
        inside 'revolution').  Multi-word phrases are checked as substrings
        because they are already specific enough.
        """
        if " " in keyword:
            return keyword in text_lower
        return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text_lower))

    @staticmethod
    def _keywords_detect(text: str) -> Dict[str, Any]:
        """Fast keyword-based detection."""
        text_lower = text.lower()

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
        # One keyword match → confidence 0.75 (on the threshold).
        # Each additional match adds 0.1 up to a cap of 0.95.
        for subject, topics in MetadataAnalyzer.KEYWORD_DATABASE.items():
            for topic, keywords in topics.items():
                match_count = sum(
                    1 for kw in keywords if MetadataAnalyzer._word_in_text(kw, text_lower)
                )
                if match_count > 0:
                    confidence = min(0.95, 0.75 + (match_count - 1) * 0.1)
                    if confidence > best["confidence"]:
                        best["subject"] = subject
                        best["topic"] = topic
                        best["confidence"] = confidence

        return best

    @staticmethod
    async def _llm_detect(text: str) -> Dict[str, Any]:
        """LLM-based detection for implicit / nuanced topics."""
        try:
            from app.services.llm_service import LLMService

            prompt = (
                'Analyze this academic text and extract the following information:\n'
                '1. Subject (e.g., Biology, History, Chemistry, Mathematics, Physics, Literature, Geography, Economics)\n'
                '2. Topic (specific topic, e.g., Photosynthesis, French Revolution)\n'
                '3. Content type (exam, guide, question, slideshow, text)\n\n'
                f'Text: "{text}"\n\n'
                'Return ONLY valid JSON with this exact format:\n'
                '{"subject": "...", "topic": "...", "content_type": "..."}'
            )

            response = await LLMService.generate_content(
                content_type="text",
                subject="General",
                topic="Metadata Extraction",
                level="expert",
                additional_context=prompt,
            )

            # Extract JSON from response (LLM may include extra text)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(response[json_start:json_end])
                return {
                    "subject": parsed.get("subject") or None,
                    "topic": parsed.get("topic") or None,
                    "content_type": parsed.get("content_type") or None,
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
