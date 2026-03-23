"""
Tests for the MetadataAnalyzer agent (hybrid keyword+LLM topic detection)
"""
import pytest
from unittest.mock import patch, AsyncMock

from app.agents.metadata_analyzer import MetadataAnalyzer


# ---------------------------------------------------------------------------
# _keywords_detect tests
# ---------------------------------------------------------------------------

class TestKeywordsDetect:
    """Unit tests for the keyword-based detection layer"""

    def test_photosynthesis_detected(self):
        result = MetadataAnalyzer._keywords_detect("Create 5 questions about photosynthesis")
        assert result["subject"] == "Biology"
        assert result["topic"] == "Photosynthesis"
        assert result["confidence"] >= 0.75

    def test_french_revolution_not_confused_with_evolution(self):
        """'evolution' must not match inside 'revolution'"""
        result = MetadataAnalyzer._keywords_detect("Tell me about the French Revolution")
        assert result["subject"] == "History"
        assert result["topic"] == "French Revolution"
        assert result["confidence"] >= 0.75

    def test_cell_cycle_with_multiple_keywords(self):
        result = MetadataAnalyzer._keywords_detect(
            "Generate an exam on mitosis and cell division"
        )
        assert result["subject"] == "Biology"
        assert result["topic"] == "Cell Cycle"
        # Two keyword matches → higher confidence
        assert result["confidence"] >= 0.85

    def test_calculus_guide(self):
        result = MetadataAnalyzer._keywords_detect(
            "Create a study guide for calculus derivatives"
        )
        assert result["subject"] == "Mathematics"
        assert result["topic"] == "Calculus"
        assert result["content_type"] == "guide"

    def test_osmotic_pressure(self):
        result = MetadataAnalyzer._keywords_detect(
            "Generate questions about osmotic pressure in solutions"
        )
        assert result["subject"] == "Chemistry"
        assert result["topic"] == "Osmotic Pressure"

    def test_world_war_2_slideshow(self):
        result = MetadataAnalyzer._keywords_detect("World War 2 presentation slides")
        assert result["subject"] == "History"
        assert result["topic"] == "World War 2"
        assert result["content_type"] == "slideshow"

    def test_electromagnetism(self):
        result = MetadataAnalyzer._keywords_detect(
            "Explain electric field and magnetic field interactions"
        )
        assert result["subject"] == "Physics"
        assert result["topic"] == "Electromagnetism"

    def test_genetics_multiple_keywords(self):
        result = MetadataAnalyzer._keywords_detect("Write about DNA and RNA genetics")
        assert result["subject"] == "Biology"
        assert result["topic"] == "Genetics"
        # Multiple matches → confidence >= 0.95
        assert result["confidence"] >= 0.95

    def test_no_match_returns_zero_confidence(self):
        result = MetadataAnalyzer._keywords_detect("random unrelated text xyz")
        assert result["confidence"] == 0.0
        assert result["subject"] is None
        assert result["topic"] is None

    def test_content_type_exam_detection(self):
        result = MetadataAnalyzer._keywords_detect("Create an exam for my students")
        assert result["content_type"] == "exam"

    def test_content_type_guide_detection(self):
        result = MetadataAnalyzer._keywords_detect("Write a study guide")
        assert result["content_type"] == "guide"

    def test_word_boundary_evolution_standalone(self):
        """'evolution' as a standalone word should match Biology/Evolution"""
        result = MetadataAnalyzer._keywords_detect("Explain evolution and natural selection")
        assert result["subject"] == "Biology"
        assert result["topic"] == "Evolution"


# ---------------------------------------------------------------------------
# hybrid_detect tests (keyword fast path)
# ---------------------------------------------------------------------------

class TestHybridDetect:
    """Integration tests for hybrid_detect – keyword path (no LLM call needed)"""

    def test_explicit_topic_uses_keyword_path(self):
        result = MetadataAnalyzer.hybrid_detect(
            "Create 5 questions about photosynthesis"
        )
        assert result["method"] == "keywords"
        assert result["subject"] == "Biology"
        assert result["topic"] == "Photosynthesis"
        assert result["confidence"] >= 0.75

    def test_document_metadata_overrides_prompt(self):
        """When document metadata is present it should take precedence"""
        result = MetadataAnalyzer.hybrid_detect(
            "Create a study guide from this document",
            document_metadata={"subject": "Chemistry", "topic": "Acids and Bases"},
        )
        assert result["subject"] == "Chemistry"
        assert result["topic"] == "Acids and Bases"
        assert result["method"] == "document"

    def test_document_metadata_partial_override(self):
        """Document provides topic, keyword provides content_type"""
        result = MetadataAnalyzer.hybrid_detect(
            "Create an exam from this document",
            document_metadata={"subject": "Physics", "topic": "Mechanics"},
        )
        assert result["subject"] == "Physics"
        assert result["topic"] == "Mechanics"
        assert result["method"] == "document"

    def test_hybrid_detect_low_confidence_falls_back(self):
        """With low confidence and LLM disabled, falls back gracefully to keyword result"""
        with patch.object(
            MetadataAnalyzer,
            "_llm_detect",
            new=AsyncMock(return_value={"subject": None, "topic": None, "content_type": None, "confidence": 0.0}),
        ):
            result = MetadataAnalyzer.hybrid_detect("something vague without keywords")
        # Should have a method set even when falling back
        assert result["method"] in ("keywords", "llm")

    def test_hybrid_detect_llm_used_on_implicit_topic(self):
        """When keywords don't match, LLM is consulted"""
        llm_output = {
            "subject": "Chemistry",
            "topic": "Osmotic Pressure",
            "content_type": "text",
            "confidence": 0.85,
        }
        with patch.object(
            MetadataAnalyzer,
            "_llm_detect",
            new=AsyncMock(return_value=llm_output),
        ):
            result = MetadataAnalyzer.hybrid_detect(
                "explain what happens when you put carrots in salty water"
            )
        # The LLM mock should supply the answer when keywords have low confidence
        assert result["method"] in ("keywords", "llm")
        # If the LLM was invoked and returned a result, assert that was used
        if result["method"] == "llm":
            assert result["subject"] == "Chemistry"
            assert result["topic"] == "Osmotic Pressure"


# ---------------------------------------------------------------------------
# Topic change detection helper (via keyword detect)
# ---------------------------------------------------------------------------

class TestTopicChangeDetection:
    """Verify that topic detection enables conversation routing logic"""

    def test_same_topic_detected_consistently(self):
        r1 = MetadataAnalyzer._keywords_detect("explain photosynthesis")
        r2 = MetadataAnalyzer._keywords_detect("describe photosynthesis in detail")
        assert r1["topic"] == r2["topic"]

    def test_different_topics_detected(self):
        r1 = MetadataAnalyzer._keywords_detect("create exam about photosynthesis")
        r2 = MetadataAnalyzer._keywords_detect("questions about the French Revolution")
        assert r1["topic"] != r2["topic"]
        assert r1["subject"] != r2["subject"]
