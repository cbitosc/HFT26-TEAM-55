"""Unit tests for Reciprocal Rank Fusion (RRF)."""

from src.backend.fusion import reciprocal_rank_fusion
from src.backend.models import CodeChunk, ScoreBreakdown, SearchResult


def test_rrf_fusion():
    c1 = CodeChunk(
        id="c1",
        path="auth/login.py",
        language="python",
        kind="function",
        symbol="login",
        start_line=1,
        end_line=5,
        code="def login(): pass",
    )
    c2 = CodeChunk(
        id="c2",
        path="auth/token.py",
        language="python",
        kind="function",
        symbol="verify",
        start_line=1,
        end_line=5,
        code="def verify(): pass",
    )
    chunks_map = {"c1": c1, "c2": c2}

    res1 = SearchResult(
        chunk_id="c1",
        evidence_id="E1",
        path="auth/login.py",
        language="python",
        kind="function",
        symbol="login",
        start_line=1,
        end_line=5,
        code="def login(): pass",
        score=10.0,
        breakdown=ScoreBreakdown(),
    )
    res2 = SearchResult(
        chunk_id="c2",
        evidence_id="E2",
        path="auth/token.py",
        language="python",
        kind="function",
        symbol="verify",
        start_line=1,
        end_line=5,
        code="def verify(): pass",
        score=8.0,
        breakdown=ScoreBreakdown(),
    )

    lexical_results = [res1, res2]
    # Semantic ranks c2 as #1 and c1 as #2
    semantic_rankings = [("c2", 0.95), ("c1", 0.80)]

    fused = reciprocal_rank_fusion(lexical_results, semantic_rankings, chunks_map, k=60, top_k=2)
    assert len(fused) == 2
    # In both, both c1 and c2 appear at ranks 1 and 2, so their RRF scores are identical:
    # 1/(60+1) + 1/(60+2)
    expected_score = round(1 / 61 + 1 / 62, 5)
    assert abs(fused[0].score - expected_score) < 0.0001
    assert fused[0].breakdown.fused_rank == 1
    assert fused[1].breakdown.fused_rank == 2
