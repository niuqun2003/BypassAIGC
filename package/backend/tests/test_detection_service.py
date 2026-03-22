"""
AIGC Detection Service Tests
TDD: write failing tests first, then implement.
"""
import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.detection_service import (
    detect_text,
    split_document_sections,
    score_to_tier,
    build_fragment_explanation,
)

# ─────────────────────────────────────────────────────────────────────────────
# Task 1: Backend Report Contract
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_CN = (
    "一、引言\n"
    "本研究旨在探讨深度学习在自然语言处理领域的应用。"
    "首先，我们回顾了相关文献。其次，提出了新的方法论框架。"
    "此外，实验结果表明该方法具有显著优势。综上所述，本文贡献如下。\n\n"
    "二、方法\n"
    "本文采用Transformer架构，结合注意力机制，实现了端到端的文本理解。"
    "值得注意的是，该模型在多个基准数据集上均取得了领先性能。"
    "与此同时，计算效率也得到了有效提升。因此，具有广泛的应用前景。"
)


def test_detect_text_returns_report_contract():
    """Task 1: Full MVP report contract must be present in detect_text output."""
    result = asyncio.run(detect_text(SAMPLE_CN, use_llm=False))

    # Top-level required fields
    assert "document_score" in result, "missing document_score"
    assert "document_tier" in result, "missing document_tier"
    assert "confidence" in result, "missing confidence"
    assert "sections" in result, "missing sections"
    assert "fragments" in result, "missing fragments"
    assert "explanations" in result, "missing explanations"
    assert "report_metadata" in result, "missing report_metadata"

    # Type checks
    assert isinstance(result["document_score"], int), "document_score must be int"
    assert isinstance(result["sections"], list), "sections must be list"
    assert isinstance(result["fragments"], list), "fragments must be list"
    assert isinstance(result["explanations"], list), "explanations must be list"

    # Score range
    assert 0 <= result["document_score"] <= 100, "document_score out of range"

    # Tier values
    assert result["document_tier"] in ("significant", "suspected", "unmarked"), \
        f"unexpected document_tier: {result['document_tier']}"


def test_detect_text_fragment_contract():
    """Task 1: Each fragment must have text, score, tier (no start/end for MVP)."""
    result = asyncio.run(detect_text(SAMPLE_CN, use_llm=False))
    for frag in result["fragments"]:
        assert "text" in frag, f"fragment missing 'text': {frag}"
        assert "score" in frag, f"fragment missing 'score': {frag}"
        assert "tier" in frag, f"fragment missing 'tier': {frag}"
        assert isinstance(frag["score"], int), "fragment score must be int"
        assert frag["tier"] in ("significant", "suspected", "unmarked"), \
            f"unexpected fragment tier: {frag['tier']}"


def test_detect_text_report_metadata_fields():
    """Task 1: report_metadata must carry processing info."""
    result = asyncio.run(detect_text(SAMPLE_CN, use_llm=False))
    meta = result["report_metadata"]
    assert "char_count" in meta
    assert "processing_time_ms" in meta
    assert "llm_used" in meta
    assert meta["llm_used"] is False  # use_llm=False


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: Document Parsing — split_document_sections
# ─────────────────────────────────────────────────────────────────────────────

def test_split_document_prefers_explicit_headings():
    """Task 2: Explicit Chinese headings should be detected as section titles."""
    text = "一、引言\n内容A\n\n二、方法\n内容B"
    sections = split_document_sections(text)
    titles = [s["title"] for s in sections]
    assert "一、引言" in titles
    assert "二、方法" in titles


def test_split_document_numeric_headings():
    """Task 2: Numeric headings like '1.' and '1.1' should be detected."""
    text = "1. 背景\n内容A\n\n2. 方法\n内容B"
    sections = split_document_sections(text)
    assert len(sections) >= 2


def test_split_document_english_headings():
    """Task 2: English chapter headings should be detected."""
    text = "Chapter 1\nIntroduction content here.\n\nChapter 2\nMethod content here."
    sections = split_document_sections(text)
    assert len(sections) >= 2


def test_split_document_fallback_pseudo_sections():
    """Task 2: No headings → fall back to paragraph groups."""
    text = (
        "这是第一段，内容足够长，没有任何标题标记。" * 3 + "\n\n"
        "这是第二段，同样没有标题，但内容依然完整。" * 3
    )
    sections = split_document_sections(text)
    assert len(sections) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Task 3: Risk Scoring — score_to_tier
# ─────────────────────────────────────────────────────────────────────────────

def test_score_to_tier_uses_dual_thresholds():
    """Task 3: score_to_tier must map correctly using configurable thresholds."""
    assert score_to_tier(80, high=70, medium=45) == "significant"
    assert score_to_tier(55, high=70, medium=45) == "suspected"
    assert score_to_tier(20, high=70, medium=45) == "unmarked"


def test_score_to_tier_boundary_values():
    """Task 3: Boundary values must fall into the correct tier."""
    assert score_to_tier(70, high=70, medium=45) == "significant"
    assert score_to_tier(69, high=70, medium=45) == "suspected"
    assert score_to_tier(45, high=70, medium=45) == "suspected"
    assert score_to_tier(44, high=70, medium=45) == "unmarked"


# ─────────────────────────────────────────────────────────────────────────────
# Task 4: Explanations — build_fragment_explanation
# ─────────────────────────────────────────────────────────────────────────────

def test_fragment_explanations_map_to_real_signals():
    """Task 4: Explanations must reference real signal keys, not free-form prose."""
    explanation = build_fragment_explanation(
        {"connector_density": 0.9},
        ["connector_density"],
    )
    assert "connector_density" in explanation["signal_keys"]
    assert "summary" in explanation
    assert isinstance(explanation["summary"], str)
    assert len(explanation["summary"]) > 0


def test_fragment_explanation_only_triggered_signals():
    """Task 4: Explanation must not include signals that did not trigger."""
    explanation = build_fragment_explanation(
        {"connector_density": 0.9, "burstiness": 0.1},
        ["connector_density"],  # only connector triggered
    )
    assert "connector_density" in explanation["signal_keys"]
    assert "burstiness" not in explanation["signal_keys"]


# ─────────────────────────────────────────────────────────────────────────────
# Task 5: Optional LLM Path
# ─────────────────────────────────────────────────────────────────────────────

def test_detect_text_succeeds_without_llm():
    """Task 5: Report must complete successfully when use_llm=False."""
    result = asyncio.run(detect_text(SAMPLE_CN, use_llm=False))
    assert result["document_score"] is not None
    assert result["report_metadata"]["llm_used"] is False


def test_detect_text_metadata_records_llm_not_used():
    """Task 5: report_metadata.llm_used must be False when LLM is disabled."""
    result = asyncio.run(detect_text(SAMPLE_CN, use_llm=False))
    assert result["report_metadata"]["llm_used"] is False
    assert "llm_available" in result["report_metadata"]
