"""Data models and schemas for NextGen Code Explorer."""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CodeChunk(BaseModel):
    """Represents a discrete semantic chunk of source code or documentation."""
    id: str
    path: str
    language: str
    kind: str  # "function", "class", "method", "doc", "window"
    symbol: str
    parent: Optional[str] = None
    start_line: int
    end_line: int
    code: str
    docstring: str = ""
    imports: List[str] = Field(default_factory=list)


class FieldMatch(BaseModel):
    """Details how a term matched within a specific document field."""
    field: str
    matched_terms: List[str]
    score_contribution: float


class ScoreBreakdown(BaseModel):
    """Explainable ranking breakdown for why a result matched."""
    matched_terms: List[str] = Field(default_factory=list)
    field_matches: List[FieldMatch] = Field(default_factory=list)
    bm25_score: float = 0.0
    boosts_applied: Dict[str, float] = Field(default_factory=dict)
    final_lexical_score: float = 0.0
    lexical_rank: Optional[int] = None
    semantic_rank: Optional[int] = None
    semantic_score: Optional[float] = None
    fused_rank: Optional[int] = None
    fused_score: Optional[float] = None
    explanation: str = ""


class SearchResult(BaseModel):
    """A single retrieved evidence item."""
    chunk_id: str
    evidence_id: str  # E1, E2, etc.
    path: str
    language: str
    kind: str
    symbol: str
    start_line: int
    end_line: int
    code: str
    docstring: str = ""
    score: float
    breakdown: ScoreBreakdown


class SearchRequest(BaseModel):
    """Request payload for searching an indexed repository."""
    session_id: str
    query: str
    top_k: int = 10
    mode: str = "hybrid"  # "lexical" | "hybrid"
    language: Optional[str] = None
    use_ai_query_rewrite: bool = False


class SearchResponse(BaseModel):
    """Search response containing verified evidence and query trace."""
    session_id: str
    query: str
    normalized_query_terms: List[str] = Field(default_factory=list)
    rewritten_query: Optional[str] = None
    mode: str
    total_results: int
    results: List[SearchResult] = Field(default_factory=list)
    query_trace_mermaid: Optional[str] = None


class IngestStatus(BaseModel):
    """Progress and statistics of the indexing pipeline."""
    session_id: str
    status: str = "idle"  # idle | extracting | scanning | parsing | indexing | ready | error
    progress_pct: int = 0
    message: str = "Ready"
    files_indexed: int = 0
    files_skipped: int = 0
    skip_reasons: Dict[str, int] = Field(default_factory=dict)
    chunks_count: int = 0
    symbols_count: int = 0
    languages: Dict[str, int] = Field(default_factory=dict)
    unique_terms_count: int = 0
    error: Optional[str] = None


class Citation(BaseModel):
    """Structured citation referencing verified evidence."""
    evidence_id: str
    path: str
    start_line: int
    end_line: int
    symbol: str


class ExplainRequest(BaseModel):
    """Request for grounded AI explanation of search results."""
    session_id: str
    query: str
    result_ids: List[str]


class ExplainResponse(BaseModel):
    """Grounded explanation citing strictly provided evidence."""
    explanation: str
    valid_citations: List[Citation] = Field(default_factory=list)
    invalid_citations_stripped: List[str] = Field(default_factory=list)
    grounded: bool = True
    model_used: Optional[str] = None
    error: Optional[str] = None


class GraphResponse(BaseModel):
    """Dependency graph Mermaid output and metrics."""
    mermaid: str
    node_count: int
    edge_count: int
    truncated: bool = False


class PostingChunk(BaseModel):
    """Posting item returned in index explorer."""
    chunk_id: str
    path: str
    symbol: str
    term_frequency: int
    fields: List[str]


class TermPosting(BaseModel):
    """Posting list details for a single term."""
    term: str
    document_frequency: int
    top_chunks: List[PostingChunk]


class FileContextResponse(BaseModel):
    """File lines context for modal inspection."""
    path: str
    total_lines: int
    start_line: int
    end_line: int
    code: str
    highlight_start: int
    highlight_end: int
