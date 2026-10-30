"""Unit tests for Featherless LLM grounding and citation validation."""

from src.backend.llm import generate_grounded_explanation, validate_citations_and_claims
from src.backend.models import ScoreBreakdown, SearchResult


def test_validate_citations_strict_stripping():
    r1 = SearchResult(
        chunk_id="c1",
        evidence_id="E1",
        path="auth/login.py",
        language="python",
        kind="function",
        symbol="login_user",
        start_line=10,
        end_line=25,
        code="def login_user(): pass",
        score=5.0,
        breakdown=ScoreBreakdown(),
    )
    evidence_map = {"E1": r1}

    # Model generates text citing real E1 and fake E99
    text_with_fake = "User login is handled in auth/login.py [E1]. Also password reset is in reset.py [E99]."

    sanitized, valid_cites, invalid = validate_citations_and_claims(text_with_fake, evidence_map)

    # Valid citation kept
    assert "[E1]" in sanitized
    assert len(valid_cites) == 1
    assert valid_cites[0].evidence_id == "E1"
    assert valid_cites[0].path == "auth/login.py"

    # Fake citation [E99] stripped
    assert "[E99]" not in sanitized
    assert "E99" in invalid


def test_offline_mode_without_api_key(monkeypatch):
    monkeypatch.setattr("src.backend.config.FEATHERLESS_API_KEY", "")
    r1 = SearchResult(
        chunk_id="c1",
        evidence_id="E1",
        path="auth/login.py",
        language="python",
        kind="function",
        symbol="login",
        start_line=1,
        end_line=5,
        code="pass",
        score=1.0,
        breakdown=ScoreBreakdown(),
    )
    resp = generate_grounded_explanation("where is login?", [r1])
    assert "unavailable" in resp.explanation.lower()
    assert resp.error is not None
