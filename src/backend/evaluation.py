"""Evaluation harness measuring retrieval metrics (Hit@1, Hit@3, MRR) for NextGen Code Explorer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.backend.inverted_index import FieldAwareIndex
from src.backend.ranker import rank_lexical
from src.backend.semantic import is_semantic_available, rank_semantic
from src.backend.fusion import reciprocal_rank_fusion
from src.backend.models import SearchResult


def evaluate_question(
    question_data: Dict[str, Any],
    results: List[SearchResult],
) -> Dict[str, Any]:
    """Check if any of the expected files or symbols appear in the retrieved results."""
    expected_files = [f.lower().replace("\\", "/") for f in question_data.get("expected_files", [])]
    expected_symbols = [s.lower() for s in question_data.get("expected_symbols", [])]

    first_hit_rank: Optional[int] = None
    hit_details: Optional[dict] = None

    for rank, res in enumerate(results, 1):
        res_path = res.path.lower().replace("\\", "/")
        res_symbol = (res.symbol or "").lower()

        # Check file match
        file_match = any(
            exp in res_path or res_path.endswith(exp) for exp in expected_files
        )
        # Check symbol match
        symbol_match = any(
            exp == res_symbol or exp in res_symbol.split(".") for exp in expected_symbols
        )

        if file_match or symbol_match:
            first_hit_rank = rank
            hit_details = {
                "matched_rank": rank,
                "matched_path": res.path,
                "matched_symbol": res.symbol,
                "evidence_id": res.evidence_id,
                "by_file": file_match,
                "by_symbol": symbol_match,
            }
            break

    hit_1 = 1.0 if first_hit_rank == 1 else 0.0
    hit_3 = 1.0 if (first_hit_rank is not None and first_hit_rank <= 3) else 0.0
    reciprocal_rank = 1.0 / first_hit_rank if first_hit_rank is not None else 0.0

    return {
        "question": question_data["question"],
        "expected_files": question_data.get("expected_files", []),
        "expected_symbols": question_data.get("expected_symbols", []),
        "notes": question_data.get("notes", ""),
        "hit_1": hit_1,
        "hit_3": hit_3,
        "reciprocal_rank": reciprocal_rank,
        "first_hit_rank": first_hit_rank,
        "hit_details": hit_details,
        "top_result_path": results[0].path if results else None,
        "top_result_symbol": results[0].symbol if results else None,
    }


def run_evaluation(
    eval_questions: List[Dict[str, Any]],
    index: FieldAwareIndex,
    top_k: int = 10,
    modes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run full evaluation suite over all questions and return summary metrics and per-question report."""
    if modes is None:
        modes = ["lexical"]
        if is_semantic_available():
            modes.append("hybrid")

    mode_reports: Dict[str, Any] = {}

    for mode in modes:
        question_evals: List[Dict[str, Any]] = []

        for q in eval_questions:
            query = q["question"]
            lex_results, _ = rank_lexical(query, index, top_k=20)

            if mode == "hybrid" and is_semantic_available():
                sem_scores = rank_semantic(query, index.chunks, index.session_id, top_k=20)
                final_results = reciprocal_rank_fusion(
                    lex_results, sem_scores, index.chunks, top_k=top_k
                )
            else:
                final_results = lex_results[:top_k]

            report = evaluate_question(q, final_results)
            question_evals.append(report)

        total = len(question_evals) or 1
        avg_hit_1 = sum(r["hit_1"] for r in question_evals) / total
        avg_hit_3 = sum(r["hit_3"] for r in question_evals) / total
        mrr = sum(r["reciprocal_rank"] for r in question_evals) / total

        mode_reports[mode] = {
            "mode": mode,
            "total_questions": len(question_evals),
            "hit_at_1": round(avg_hit_1, 4),
            "hit_at_3": round(avg_hit_3, 4),
            "mrr": round(mrr, 4),
            "hit_at_1_pct": f"{avg_hit_1 * 100:.1f}%",
            "hit_at_3_pct": f"{avg_hit_3 * 100:.1f}%",
            "questions": question_evals,
        }

    return {
        "modes": mode_reports,
        "semantic_available": is_semantic_available(),
    }


def save_eval_results_to_docs(eval_summary: Dict[str, Any], output_path: Optional[Path] = None) -> None:
    """Save evaluation metrics to docs/eval_results.json."""
    if output_path is None:
        from src.backend import config
        output_path = config.BASE_DIR / "docs" / "eval_results.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)
