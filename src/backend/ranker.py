"""Lexical BM25F ranker with field weights, boosts, and explainable breakdowns."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from src.backend import config
from src.backend.inverted_index import FieldAwareIndex
from src.backend.models import CodeChunk, FieldMatch, ScoreBreakdown, SearchResult
from src.backend.tokenizer import split_identifier, tokenize


DOC_INTENT_TERMS: Set[str] = {
    "what", "how", "setup", "install", "installation", "guide", "overview",
    "architecture", "readme", "start", "config", "configuration", "run", "contribute"
}


def rank_lexical(
    query: str,
    index: FieldAwareIndex,
    top_k: int = 10,
    language_filter: Optional[str] = None,
) -> Tuple[List[SearchResult], List[str]]:
    """Perform BM25F lexical ranking over the field-aware inverted index.

    Returns:
        (results, normalized_query_terms)
    """
    raw_query = query.strip()
    if not raw_query or index.total_docs == 0:
        return [], []

    # Tokenize query removing conversational filler words
    query_terms = tokenize(raw_query, remove_stopwords=True, apply_stemming=True, preserve_raw=True)
    if not query_terms:
        # If all tokens were stopwords, fallback to preserving tokens without stopword filtering
        query_terms = tokenize(raw_query, remove_stopwords=False, apply_stemming=True, preserve_raw=True)

    # Unique query terms to avoid duplicate scoring
    unique_query_terms = list(dict.fromkeys(query_terms))

    field_weights = {
        "symbol": config.WEIGHT_SYMBOL,
        "path": config.WEIGHT_PATH,
        "docstring": config.WEIGHT_DOCSTRING,
        "code": config.WEIGHT_CODE,
    }

    k1 = config.BM25_K1
    b = config.BM25_B

    # Candidate chunk IDs -> accumulator
    # candidate_scores[cid] = {"bm25": float, "field_scores": {f: float}, "matched_terms": set(), "field_terms": {f: set()}}
    candidate_data: Dict[str, dict] = {}

    for term in unique_query_terms:
        idf = index.compute_idf(term)
        if idf <= 0.0:
            continue

        # Find all chunks containing this term in any field
        term_chunks: Set[str] = set()
        for field in index.fields:
            if term in index.postings[field]:
                term_chunks.update(index.postings[field][term].keys())

        for cid in term_chunks:
            chunk = index.chunks.get(cid)
            if not chunk:
                continue

            # Optional language filter
            if language_filter and chunk.language.lower() != language_filter.lower():
                continue

            if cid not in candidate_data:
                candidate_data[cid] = {
                    "bm25": 0.0,
                    "field_contrib": {f: 0.0 for f in index.fields},
                    "matched_terms": set(),
                    "field_terms": {f: set() for f in index.fields},
                }

            # Calculate normalized term frequency across fields for BM25F
            weighted_norm_tf = 0.0
            for field in index.fields:
                tf_entry = index.postings[field].get(term, {}).get(cid)
                if tf_entry:
                    raw_tf = tf_entry["tf"]
                    doc_len = index.doc_lengths[field].get(cid, 0)
                    avg_len = index.avg_doc_len.get(field, 1.0) or 1.0
                    len_norm = 1.0 - b + b * (doc_len / avg_len)
                    norm_tf = raw_tf / len_norm if len_norm > 0 else raw_tf
                    field_contrib = field_weights[field] * norm_tf

                    weighted_norm_tf += field_contrib
                    candidate_data[cid]["field_contrib"][field] += field_contrib * idf
                    candidate_data[cid]["field_terms"][field].add(term)

            # BM25 saturation function
            term_bm25 = idf * (weighted_norm_tf * (k1 + 1.0)) / (weighted_norm_tf + k1)
            candidate_data[cid]["bm25"] += term_bm25
            candidate_data[cid]["matched_terms"].add(term)

    # Compute explicit boosts and build SearchResults
    scored_results: List[SearchResult] = []
    clean_query_lower = re.sub(r"[_\-./\s]+", "", raw_query).lower()
    is_doc_intent = any(w in raw_query.lower().split() for w in DOC_INTENT_TERMS)

    for cid, data in candidate_data.items():
        chunk = index.chunks[cid]
        bm25_score = data["bm25"]
        boosts: Dict[str, float] = {}

        # 1. Symbol match boost
        chunk_symbol_clean = re.sub(r"[_\-./\s]+", "", chunk.symbol or "").lower()
        symbol_tokens = [t.lower() for t in split_identifier(chunk.symbol or "")]

        if chunk.symbol:
            if (
                clean_query_lower == chunk_symbol_clean
                or clean_query_lower in [t.lower() for t in (chunk.symbol.split(".")) if t]
                or chunk.symbol.lower() in raw_query.lower().split()
            ):
                boosts["Exact Symbol Match"] = config.BOOST_EXACT_SYMBOL
            elif any(qt in symbol_tokens for qt in unique_query_terms):
                boosts["Symbol Match"] = config.BOOST_EXACT_SYMBOL * 0.75

        # 2. Path match boost
        path_lower = chunk.path.lower()
        path_matches = [t for t in unique_query_terms if t in path_lower]
        if path_matches:
            boosts["Path Match"] = config.BOOST_PATH_MATCH * min(len(path_matches), 2)

        # 3. Documentation intent boost
        if is_doc_intent and (chunk.kind == "doc" or "readme" in path_lower or "doc" in path_lower):
            boosts["Documentation Intent"] = config.BOOST_DOCS_FOR_HELP

        total_boost = sum(boosts.values())
        final_score = round(bm25_score + total_boost, 4)

        # Field matches for score breakdown
        field_matches = [
            FieldMatch(
                field=f,
                matched_terms=sorted(list(data["field_terms"][f])),
                score_contribution=round(data["field_contrib"][f], 3),
            )
            for f in index.fields
            if data["field_terms"][f]
        ]

        # Generate human-readable explanation
        matched_str = ", ".join(f"'{m}'" for m in sorted(list(data["matched_terms"])))
        matched_fields_str = ", ".join(fm.field for fm in field_matches)
        boost_str = f" + boosts ({', '.join(boosts.keys())})" if boosts else ""
        explanation = (
            f"Matched terms [{matched_str}] in [{matched_fields_str}]. "
            f"BM25F score: {bm25_score:.2f}{boost_str} = {final_score:.2f}."
        )

        breakdown = ScoreBreakdown(
            matched_terms=sorted(list(data["matched_terms"])),
            field_matches=field_matches,
            bm25_score=round(bm25_score, 4),
            boosts_applied=boosts,
            final_lexical_score=final_score,
            explanation=explanation,
        )

        scored_results.append(
            SearchResult(
                chunk_id=chunk.id,
                evidence_id="",  # Assigned after sorting/filtering
                path=chunk.path,
                language=chunk.language,
                kind=chunk.kind,
                symbol=chunk.symbol,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                code=chunk.code,
                docstring=chunk.docstring,
                score=final_score,
                breakdown=breakdown,
            )
        )

    # Sort results by final score descending
    scored_results.sort(key=lambda x: x.score, reverse=True)

    # Assign evidence IDs (E1, E2, ...) and ranks
    final_results = scored_results[:top_k]
    for idx, res in enumerate(final_results, 1):
        res.evidence_id = f"E{idx}"
        res.breakdown.lexical_rank = idx

    return final_results, unique_query_terms
