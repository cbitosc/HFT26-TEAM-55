"""Handcrafted, field-aware inverted index for NextGen Code Explorer.

Indexes symbols, paths, docstrings, and code with BM25F document-length normalization,
frequency tracking, positional postings, and disk persistence.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.backend import config
from src.backend.models import CodeChunk, PostingChunk, TermPosting
from src.backend.tokenizer import tokenize


class FieldAwareIndex:
    """In-memory and disk-persisted field-aware inverted index."""

    def __init__(self, session_id: str, data_dir: Optional[Path] = None):
        self.session_id = session_id
        self.data_dir = data_dir or (config.DATA_DIR / session_id)
        self.index_file = self.data_dir / "inverted_index.json"

        # Chunks storage: chunk_id -> CodeChunk
        self.chunks: Dict[str, CodeChunk] = {}

        # Fields: symbol, path, docstring, code
        self.fields = ["symbol", "path", "docstring", "code"]

        # Postings structure:
        # postings[field][term] = {chunk_id: {"tf": int, "positions": List[int]}}
        self.postings: Dict[str, Dict[str, Dict[str, dict]]] = {f: {} for f in self.fields}

        # Document lengths:
        # doc_lengths[field][chunk_id] = int
        self.doc_lengths: Dict[str, Dict[str, int]] = {f: {} for f in self.fields}

        # Average document lengths per field
        self.avg_doc_len: Dict[str, float] = {f: 0.0 for f in self.fields}

        # Document frequency across any field: term -> int (count of unique chunks)
        self.doc_freq: Dict[str, int] = {}

        # Set of all unique terms
        self.vocabulary: Set[str] = set()

    @property
    def total_docs(self) -> int:
        return len(self.chunks)

    def add_chunk(self, chunk: CodeChunk) -> None:
        """Tokenize and index a CodeChunk across all distinct fields."""
        self.chunks[chunk.id] = chunk

        field_texts = {
            "symbol": chunk.symbol or "",
            "path": chunk.path or "",
            "docstring": chunk.docstring or "",
            "code": chunk.code or "",
        }

        chunk_terms_all: Set[str] = set()

        for field_name, text in field_texts.items():
            tokens = tokenize(text, remove_stopwords=False, apply_stemming=True, preserve_raw=True)
            self.doc_lengths[field_name][chunk.id] = len(tokens)

            # Build positions and frequency for this field
            field_postings = self.postings[field_name]
            for pos, term in enumerate(tokens):
                chunk_terms_all.add(term)
                self.vocabulary.add(term)

                if term not in field_postings:
                    field_postings[term] = {}

                if chunk.id not in field_postings[term]:
                    field_postings[term][chunk.id] = {"tf": 0, "positions": []}

                field_postings[term][chunk.id]["tf"] += 1
                field_postings[term][chunk.id]["positions"].append(pos)

        # Update global document frequency
        for term in chunk_terms_all:
            self.doc_freq[term] = self.doc_freq.get(term, 0) + 1

    def finalize(self) -> None:
        """Compute aggregate statistics (average document lengths) after indexing."""
        n = max(self.total_docs, 1)
        for field in self.fields:
            total_len = sum(self.doc_lengths[field].values())
            self.avg_doc_len[field] = total_len / n

    def compute_idf(self, term: str) -> float:
        """Calculate Lucene/BM25 IDF for a term: ln(1 + (N - nt + 0.5) / (nt + 0.5))."""
        nt = self.doc_freq.get(term, 0)
        n = self.total_docs
        if nt == 0 or n == 0:
            return 0.0
        return math.log(1.0 + (n - nt + 0.5) / (nt + 0.5))

    def get_term_postings(self, term: str, max_results: int = 50) -> TermPosting:
        """Inspect postings list for a given term across all fields."""
        normalized_tokens = tokenize(term, remove_stopwords=False, apply_stemming=True, preserve_raw=True)
        query_term = normalized_tokens[0] if normalized_tokens else term.lower()

        # Find all chunks containing this term
        matched_chunks: Dict[str, dict] = {}

        for field in self.fields:
            if query_term in self.postings[field]:
                for cid, data in self.postings[field][query_term].items():
                    if cid not in matched_chunks:
                        chunk = self.chunks.get(cid)
                        matched_chunks[cid] = {
                            "chunk_id": cid,
                            "path": chunk.path if chunk else "",
                            "symbol": chunk.symbol if chunk else "",
                            "term_frequency": 0,
                            "fields": [],
                        }
                    matched_chunks[cid]["term_frequency"] += data["tf"]
                    matched_chunks[cid]["fields"].append(field)

        top_chunks_list = sorted(
            matched_chunks.values(),
            key=lambda x: x["term_frequency"],
            reverse=True,
        )[:max_results]

        return TermPosting(
            term=query_term,
            document_frequency=self.doc_freq.get(query_term, 0),
            top_chunks=[PostingChunk(**item) for item in top_chunks_list],
        )

    def save_to_disk(self) -> None:
        """Persist index structures and chunks to disk in JSON format."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "session_id": self.session_id,
            "avg_doc_len": self.avg_doc_len,
            "doc_freq": self.doc_freq,
            "vocabulary": list(self.vocabulary),
            "doc_lengths": self.doc_lengths,
            "postings": self.postings,
            "chunks": {cid: chunk.model_dump() for cid, chunk in self.chunks.items()},
        }
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

    @classmethod
    def load_from_disk(cls, session_id: str, data_dir: Optional[Path] = None) -> Optional["FieldAwareIndex"]:
        """Load index from disk if existing."""
        path = (data_dir or (config.DATA_DIR / session_id)) / "inverted_index.json"
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            idx = cls(session_id, data_dir)
            idx.avg_doc_len = data.get("avg_doc_len", {f: 0.0 for f in idx.fields})
            idx.doc_freq = data.get("doc_freq", {})
            idx.vocabulary = set(data.get("vocabulary", []))
            idx.doc_lengths = data.get("doc_lengths", {f: {} for f in idx.fields})
            idx.postings = data.get("postings", {f: {} for f in idx.fields})
            idx.chunks = {
                cid: CodeChunk(**c_data) for cid, c_data in data.get("chunks", {}).items()
            }
            return idx
        except Exception:
            return None
