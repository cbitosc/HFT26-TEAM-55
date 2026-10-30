"""Command-line evaluation runner and benchmark harness for NextGen Code Explorer.

Evaluates Hit@1, Hit@3, and MRR metrics across verified questions, prints an
ASCII comparison table, and saves results to docs/eval_results.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.backend import config
from src.backend.evaluation import run_evaluation, save_eval_results_to_docs
from src.backend.ingest import extract_zip_safely, scan_repository
from src.backend.inverted_index import FieldAwareIndex
from src.backend.parsers import parse_source_file
from src.backend.semantic import compute_and_cache_embeddings, is_semantic_available


def index_target_repo(repo_path: Path, session_id: str = "eval_session") -> FieldAwareIndex:
    """Scan, parse, and build an inverted index for a repository folder or ZIP."""
    if repo_path.is_file() and repo_path.suffix.lower() == ".zip":
        extract_dir = config.DATA_DIR / session_id / "raw"
        extract_dir.mkdir(parents=True, exist_ok=True)
        extract_zip_safely(repo_path, extract_dir)
        scan_dir = extract_dir
    else:
        scan_dir = repo_path

    accepted_files, skipped = scan_repository(scan_dir)
    print(f"[*] Scanning {repo_path}: found {len(accepted_files)} admitted files (skipped {sum(skipped.values())})")

    index = FieldAwareIndex(session_id)
    all_chunks = []

    for rel_path, abs_path in accepted_files:
        chunks = parse_source_file(rel_path, abs_path)
        all_chunks.extend(chunks)
        for c in chunks:
            index.add_chunk(c)

    index.finalize()
    index.save_to_disk()
    print(f"[*] Indexed {len(all_chunks)} chunks across {len(index.vocabulary)} unique terms.")

    if is_semantic_available():
        print("[*] Computing semantic embeddings...")
        compute_and_cache_embeddings(all_chunks, session_id)

    return index


def main():
    parser = argparse.ArgumentParser(description="NextGen Code Explorer Evaluation Harness")
    parser.add_argument(
        "--repo",
        type=str,
        default=str(config.SAMPLE_REPO_DIR),
        help="Path to repository folder or ZIP archive (defaults to tests/sample_repo)",
    )
    parser.add_argument(
        "--questions",
        type=str,
        default=str(BASE_DIR / "tests" / "eval_questions.json"),
        help="Path to eval questions JSON fixture",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of retrieved results to inspect per question",
    )
    parser.add_argument(
        "--session",
        type=str,
        default="sample_repo",
        help="Session identifier",
    )
    args = parser.parse_args()

    repo_path = Path(args.repo).resolve()
    questions_file = Path(args.questions).resolve()

    if not questions_file.exists():
        print(f"[!] Error: questions file not found: {questions_file}")
        sys.exit(1)

    with open(questions_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print("=" * 80)
    print(f" NEXTGEN CODE EXPLORER - EVALUATION HARNESS")
    print(f" Repository: {repo_path}")
    print(f" Questions:  {len(questions)} verified benchmark questions")
    print(f" Semantic:   {'Available (all-MiniLM-L6-v2)' if is_semantic_available() else 'Unavailable (Lexical Mode)'}")
    print("=" * 80)

    # Build or retrieve index
    index = index_target_repo(repo_path, session_id=args.session)

    # Run evaluation
    results = run_evaluation(questions, index, top_k=args.top_k)

    # Print summary tables
    for mode, data in results["modes"].items():
        print(f"\n Mode: [{mode.upper()}]")
        print("-" * 80)
        print(f" Total Questions: {data['total_questions']}")
        print(f" Hit@1:           {data['hit_at_1_pct']} ({data['hit_at_1']})")
        print(f" Hit@3:           {data['hit_at_3_pct']} ({data['hit_at_3']})")
        print(f" MRR:             {data['mrr']}")
        print("-" * 80)
        print(f"{'#':<3} {'Question':<45} {'Hit@1':<7} {'Hit@3':<7} {'Rank':<6} {'Top Match':<20}")
        print("-" * 80)
        for i, q in enumerate(data["questions"], 1):
            q_text = q["question"][:42] + "..." if len(q["question"]) > 42 else q["question"]
            h1 = "PASS" if q["hit_1"] > 0 else "FAIL"
            h3 = "PASS" if q["hit_3"] > 0 else "FAIL"
            rank_str = str(q["first_hit_rank"]) if q["first_hit_rank"] else "-"
            top_symbol = q["top_result_symbol"] or (Path(q["top_result_path"]).name if q["top_result_path"] else "-")
            print(f"{i:<3} {q_text:<45} {h1:<7} {h3:<7} {rank_str:<6} {top_symbol[:20]:<20}")

    # Save to docs/eval_results.json
    save_eval_results_to_docs(results)
    print("\n[+] Benchmark results successfully saved to docs/eval_results.json\n")


if __name__ == "__main__":
    main()
