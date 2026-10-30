"""Reciprocal Rank Fusion (RRF) combining lexical and semantic rankings."""

from __future__ import annotations

from typing import Dict, List, Optional
from src.backend import config
from src.backend.models import CodeChunk, ScoreBreakdown, SearchResult


def reciprocal_rank_fusion(
    lexical_results: List[SearchResult],
    semantic_rankings: List[tuple[str, float]],  # List of (chunk_id, cosine_sim)
    chunks_map: Dict[str, CodeChunk],
    k: int = config.RRF_K,
    top_k: int = 10,
) -> List[SearchResult]:
    """Fuse lexical and semantic result lists using Reciprocal Rank Fusion.

    RRF_score(d) = 1 / (k + rank_lexical(d)) + 1 / (k + rank_semantic(d))
    """
    if not semantic_rankings:
        # No semantic rankings available: keep lexical results
        for idx, res in enumerate(lexical_results[:top_k], 1):
            res.evidence_id = f"E{idx}"
            res.breakdown.lexical_rank = idx
            res.breakdown.fused_rank = idx
            res.breakdown.fused_score = round(res.score, 4)
        return lexical_results[:top_k]

    # Map chunk_id -> lexical rank & result
    lexical_map: Dict[str, tuple[int, SearchResult]] = {}
    for rank, res in enumerate(lexical_results, 1):
        lexical_map[res.chunk_id] = (rank, res)

    # Map chunk_id -> semantic rank & score
    semantic_map: Dict[str, tuple[int, float]] = {}
    for rank, (cid, sim) in enumerate(semantic_rankings, 1):
        semantic_map[cid] = (rank, sim)

    # Union of all candidate chunk IDs
    all_candidate_ids = set(lexical_map.keys()).union(set(semantic_map.keys()))

    fused_candidates: List[dict] = []
    for cid in all_candidate_ids:
        chunk = chunks_map.get(cid)
        if not chunk:
            continue

        rrf_score = 0.0
        lex_rank = None
        lex_res = None
        if cid in lexical_map:
            lex_rank, lex_res = lexical_map[cid]
            rrf_score += 1.0 / (k + lex_rank)

        sem_rank = None
        sem_sim = None
        if cid in semantic_map:
            sem_rank, sem_sim = semantic_map[cid]
            rrf_score += 1.0 / (k + sem_rank)

        fused_candidates.append({
            "chunk_id": cid,
            "chunk": chunk,
            "rrf_score": rrf_score,
            "lex_rank": lex_rank,
            "lex_res": lex_res,
            "sem_rank": sem_rank,
            "sem_sim": sem_sim,
        })

    # Sort descending by RRF score
    fused_candidates.sort(key=lambda x: x["rrf_score"], reverse=True)
    top_fused = fused_candidates[:top_k]

    final_results: List[SearchResult] = []
    for idx, item in enumerate(top_fused, 1):
        cid = item["chunk_id"]
        chunk = item["chunk"]
        lex_res = item["lex_res"]
        lex_rank = item["lex_rank"]
        sem_rank = item["sem_rank"]
        sem_sim = item["sem_sim"]
        rrf_score = item["rrf_score"]

        if lex_res:
            breakdown = lex_res.breakdown.model_copy()
        else:
            breakdown = ScoreBreakdown(
                matched_terms=[],
                field_matches=[],
                bm25_score=0.0,
                boosts_applied={},
                final_lexical_score=0.0,
            )

        breakdown.lexical_rank = lex_rank
        breakdown.semantic_rank = sem_rank
        breakdown.semantic_score = round(sem_sim, 4) if sem_sim is not None else None
        breakdown.fused_rank = idx
        breakdown.fused_score = round(rrf_score, 6)

        explanation_parts = [
            f"Hybrid RRF (k={k}): Fused rank #{idx} (score {rrf_score:.5f})."
        ]
        if lex_rank is not None:
            explanation_parts.append(f"Lexical rank #{lex_rank}.")
        else:
            explanation_parts.append("Not in top lexical results.")
        if sem_rank is not None:
            explanation_parts.append(f"Semantic rank #{sem_rank} (cos sim: {sem_sim:.3f}).")

        breakdown.explanation = " ".join(explanation_parts)

        final_results.append(
            SearchResult(
                chunk_id=chunk.id,
                evidence_id=f"E{idx}",
                path=chunk.path,
                language=chunk.language,
                kind=chunk.kind,
                symbol=chunk.symbol,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                code=chunk.code,
                docstring=chunk.docstring,
                score=round(rrf_score, 5),
                breakdown=breakdown,
            )
        )

    return final_results
