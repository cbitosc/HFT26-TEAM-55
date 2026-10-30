"""Optional local semantic search with sentence-transformers and all-MiniLM-L6-v2.

Loads lazily and caches chunk embeddings on disk. If sentence-transformers is not
installed, gracefully disables itself so the application continues in lexical-only mode.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.backend import config
from src.backend.models import CodeChunk

_MODEL = None
_IS_AVAILABLE: Optional[bool] = None


def is_semantic_available() -> bool:
    """Check if sentence-transformers is installed and loadable."""
    global _IS_AVAILABLE
    if _IS_AVAILABLE is not None:
        return _IS_AVAILABLE

    try:
        import sentence_transformers  # noqa: F401
        _IS_AVAILABLE = True
    except Exception:
        _IS_AVAILABLE = False

    return _IS_AVAILABLE


def get_model():
    """Lazily load the all-MiniLM-L6-v2 embedding model."""
    global _MODEL
    if _MODEL is None:
        if not is_semantic_available():
            return None
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def chunk_to_embedding_text(chunk: CodeChunk) -> str:
    """Format chunk metadata and code prefix for embedding."""
    lines = chunk.code.splitlines()[:15]
    code_preview = "\n".join(lines)
    parts = [
        f"File: {chunk.path}",
        f"Symbol: {chunk.symbol or 'none'} ({chunk.kind})",
    ]
    if chunk.docstring:
        parts.append(f"Description: {chunk.docstring[:200]}")
    if code_preview:
        parts.append(f"Code:\n{code_preview}")
    return "\n".join(parts)


def compute_and_cache_embeddings(
    chunks: List[CodeChunk],
    session_id: str,
    data_dir: Optional[Path] = None,
) -> bool:
    """Compute embeddings for all chunks and persist to embeddings.json."""
    if not is_semantic_available() or not chunks:
        return False

    model = get_model()
    if model is None:
        return False

    session_dir = data_dir or (config.DATA_DIR / session_id)
    cache_path = session_dir / "embeddings.json"

    texts = [chunk_to_embedding_text(c) for c in chunks]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    cache_data = {
        chunk.id: emb.tolist() for chunk, emb in zip(chunks, embeddings)
    }

    try:
        session_dir.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)
        return True
    except Exception:
        return False


def load_embeddings(session_id: str, data_dir: Optional[Path] = None) -> Dict[str, List[float]]:
    """Load cached embeddings from disk."""
    session_dir = data_dir or (config.DATA_DIR / session_id)
    cache_path = session_dir / "embeddings.json"
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two normalized vectors."""
    dot = sum(a * b for a, b in zip(vec1, vec2))
    return float(dot)


def rank_semantic(
    query: str,
    chunks: Dict[str, CodeChunk],
    session_id: str,
    top_k: int = 20,
    language_filter: Optional[str] = None,
    data_dir: Optional[Path] = None,
) -> List[Tuple[str, float]]:
    """Rank chunks using semantic cosine similarity against the query embedding.

    Returns:
        List of (chunk_id, semantic_score) tuples sorted descending by score.
    """
    if not is_semantic_available():
        return []

    model = get_model()
    if model is None:
        return []

    embeddings = load_embeddings(session_id, data_dir)
    if not embeddings:
        return []

    query_emb = model.encode([query], normalize_embeddings=True)[0].tolist()

    scores: List[Tuple[str, float]] = []
    for cid, emb in embeddings.items():
        chunk = chunks.get(cid)
        if not chunk:
            continue
        if language_filter and chunk.language.lower() != language_filter.lower():
            continue

        score = cosine_similarity(query_emb, emb)
        scores.append((cid, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]
