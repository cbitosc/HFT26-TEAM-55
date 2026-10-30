"""FastAPI application for NextGen Code Explorer.

Exposes REST APIs for ZIP upload, progress tracking, lexical/hybrid search,
strict grounded AI explanation, dependency graph, index inspection, and evaluation.
Serves the single-page frontend static files.
"""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.backend import config
from src.backend.evaluation import run_evaluation, save_eval_results_to_docs
from src.backend.fusion import reciprocal_rank_fusion
from src.backend.graph import build_dependency_graph, generate_query_trace_mermaid
from src.backend.ingest import extract_zip_safely, scan_repository
from src.backend.inverted_index import FieldAwareIndex
from src.backend.llm import generate_grounded_explanation, rewrite_query_with_ai
from src.backend.models import (
    ExplainRequest,
    ExplainResponse,
    FileContextResponse,
    GraphResponse,
    IngestStatus,
    SearchRequest,
    SearchResponse,
    TermPosting,
)
from src.backend.parsers import parse_source_file
from src.backend.ranker import rank_lexical
from src.backend.semantic import compute_and_cache_embeddings, is_semantic_available, rank_semantic

# Initialize FastAPI app
app = FastAPI(
    title="NextGen Code Explorer",
    description="Explainable Code Search and Grounded AI Code Intelligence",
    version="1.0.0",
)

# Enable CORS for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session tracking state
SESSIONS_STATUS: Dict[str, IngestStatus] = {}
SESSIONS_INDEX: Dict[str, FieldAwareIndex] = {}

FRONTEND_DIR = config.BASE_DIR / "src" / "frontend"


def get_or_load_index(session_id: str) -> Optional[FieldAwareIndex]:
    """Retrieve index from memory or load from disk persistence."""
    if session_id in SESSIONS_INDEX:
        return SESSIONS_INDEX[session_id]

    idx = FieldAwareIndex.load_from_disk(session_id)
    if idx:
        SESSIONS_INDEX[session_id] = idx
        return idx
    return None


def run_indexing_pipeline(session_id: str, repo_raw_dir: Path) -> None:
    """Background task executing the complete ingestion and indexing workflow."""
    status = SESSIONS_STATUS.get(session_id)
    if not status:
        return

    try:
        # Phase 1: Scanning
        status.status = "scanning"
        status.progress_pct = 25
        status.message = "Scanning files and applying exclusions..."

        accepted_files, skipped_stats = scan_repository(repo_raw_dir)
        status.files_indexed = len(accepted_files)
        status.files_skipped = sum(skipped_stats.values())
        status.skip_reasons = skipped_stats

        # Phase 2: Parsing
        status.status = "parsing"
        status.progress_pct = 50
        status.message = f"Parsing {len(accepted_files)} source files into semantic chunks..."

        all_chunks = []
        languages_count: Dict[str, int] = {}
        symbols_found = 0

        for rel_path, abs_path in accepted_files:
            chunks = parse_source_file(rel_path, abs_path)
            all_chunks.extend(chunks)
            for c in chunks:
                if c.symbol and not c.symbol.startswith("<"):
                    symbols_found += 1
                languages_count[c.language] = languages_count.get(c.language, 0) + 1

        status.chunks_count = len(all_chunks)
        status.symbols_count = symbols_found
        status.languages = languages_count

        # Phase 3: Inverted Indexing
        status.status = "indexing"
        status.progress_pct = 75
        status.message = "Building field-aware inverted index (symbols, paths, docstrings, code)..."

        index = FieldAwareIndex(session_id)
        for chunk in all_chunks:
            index.add_chunk(chunk)
        index.finalize()
        index.save_to_disk()

        # Phase 4: Optional Semantic Embedding
        if is_semantic_available():
            status.message = "Computing semantic embeddings..."
            compute_and_cache_embeddings(all_chunks, session_id)

        SESSIONS_INDEX[session_id] = index
        status.unique_terms_count = len(index.vocabulary)
        status.status = "ready"
        status.progress_pct = 100
        status.message = "Repository indexed and ready for exploration."

    except Exception as e:
        status.status = "error"
        status.error = str(e)
        status.message = f"Indexing failed: {e}"


@app.get("/api/health")
def health():
    """Health check endpoint indicating AI and Semantic capabilities."""
    has_api_key = bool(config.FEATHERLESS_API_KEY)
    return {
        "status": "ok",
        "app": config.APP_TITLE,
        "ai_available": has_api_key,
        "semantic_available": is_semantic_available(),
        "featherless_model": config.FEATHERLESS_MODEL if has_api_key else None,
        "active_sessions": list(SESSIONS_STATUS.keys()),
    }


@app.post("/api/upload")
async def upload_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload a source code ZIP archive to extract and index."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip archives are supported.")

    session_id = uuid.uuid4().hex[:12]
    session_dir = config.DATA_DIR / session_id
    raw_dir = session_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    status = IngestStatus(
        session_id=session_id,
        status="extracting",
        progress_pct=10,
        message="Validating and safely extracting ZIP archive...",
    )
    SESSIONS_STATUS[session_id] = status

    try:
        content = await file.read()
        max_bytes = config.MAX_ZIP_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"Archive size exceeds maximum allowed limit of {config.MAX_ZIP_SIZE_MB} MB",
            )

        extract_zip_safely(content, raw_dir)
    except Exception as e:
        status.status = "error"
        status.error = str(e)
        raise HTTPException(status_code=400, detail=f"Archive extraction failed: {e}")

    background_tasks.add_task(run_indexing_pipeline, session_id, raw_dir)
    return {"session_id": session_id, "status": "processing"}


@app.post("/api/sample")
def load_sample_project(background_tasks: BackgroundTasks):
    """Load and index the bundled sample repository (ShopStream) for fast evaluation."""
    sample_dir = config.SAMPLE_REPO_DIR
    if not sample_dir.exists():
        raise HTTPException(status_code=404, detail="Sample repo directory not found.")

    session_id = "sample_repo"
    session_dir = config.DATA_DIR / session_id
    raw_dir = session_dir / "raw"

    # Copy sample repo contents to session raw dir
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    shutil.copytree(sample_dir, raw_dir)

    status = IngestStatus(
        session_id=session_id,
        status="scanning",
        progress_pct=15,
        message="Loading verified sample project...",
    )
    SESSIONS_STATUS[session_id] = status

    # Run indexing
    background_tasks.add_task(run_indexing_pipeline, session_id, raw_dir)
    return {"session_id": session_id, "status": "processing"}


@app.post("/api/index-path")
def index_local_path(
    background_tasks: BackgroundTasks,
    folder_path: str = Query(..., description="Local folder path to index"),
):
    """Index a local repository path (development mode only, disabled by default)."""
    if not config.ENABLE_LOCAL_PATH:
        raise HTTPException(
            status_code=403,
            detail="Local folder indexing is disabled by default. Set ENABLE_LOCAL_PATH=1 to enable.",
        )

    target_path = Path(folder_path).resolve()
    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(status_code=400, detail="Specified folder path does not exist or is not a directory.")

    session_id = f"local_{uuid.uuid4().hex[:8]}"
    session_dir = config.DATA_DIR / session_id
    raw_dir = session_dir / "raw"

    # Copy files
    shutil.copytree(target_path, raw_dir, dirs_exist_ok=True)

    status = IngestStatus(
        session_id=session_id,
        status="scanning",
        progress_pct=15,
        message="Scanning local path...",
    )
    SESSIONS_STATUS[session_id] = status

    background_tasks.add_task(run_indexing_pipeline, session_id, raw_dir)
    return {"session_id": session_id, "status": "processing"}


@app.get("/api/status/{session_id}", response_model=IngestStatus)
def get_status(session_id: str):
    """Retrieve indexing progress and statistics for a given session."""
    status = SESSIONS_STATUS.get(session_id)
    if not status:
        # Check if index already exists on disk
        idx = get_or_load_index(session_id)
        if idx:
            return IngestStatus(
                session_id=session_id,
                status="ready",
                progress_pct=100,
                message="Loaded from disk.",
                files_indexed=len(set(c.path for c in idx.chunks.values())),
                chunks_count=idx.total_docs,
                symbols_count=sum(1 for c in idx.chunks.values() if c.symbol),
                unique_terms_count=len(idx.vocabulary),
            )
        raise HTTPException(status_code=404, detail="Session not found.")
    return status


@app.get("/api/sessions")
def list_sessions():
    """List available indexed sessions."""
    sessions = []
    # Check sessions directory
    if config.DATA_DIR.exists():
        for item in config.DATA_DIR.iterdir():
            if item.is_dir():
                idx_file = item / "inverted_index.json"
                status_obj = SESSIONS_STATUS.get(item.name)
                sessions.append({
                    "session_id": item.name,
                    "has_index": idx_file.exists(),
                    "status": status_obj.status if status_obj else ("ready" if idx_file.exists() else "unknown"),
                })
    return {"sessions": sessions}


@app.post("/api/search", response_model=SearchResponse)
def search(request: SearchRequest):
    """Execute lexical or hybrid search over the indexed codebase."""
    index = get_or_load_index(request.session_id)
    if not index:
        raise HTTPException(status_code=404, detail="Session index not found. Please upload or index first.")

    active_query = request.query.strip()
    rewritten_query = None

    # Step 1: Optional AI query expansion
    if request.use_ai_query_rewrite and config.FEATHERLESS_API_KEY:
        expanded_terms = rewrite_query_with_ai(active_query)
        if expanded_terms:
            rewritten_query = " ".join(expanded_terms)
            active_query = f"{active_query} {rewritten_query}"

    # Step 2: Lexical Ranking
    lex_results, norm_terms = rank_lexical(
        active_query,
        index,
        top_k=max(request.top_k, 20),
        language_filter=request.language,
    )

    # Step 3: Hybrid RRF (if requested and semantic available)
    if request.mode == "hybrid" and is_semantic_available():
        sem_scores = rank_semantic(
            active_query,
            index.chunks,
            request.session_id,
            top_k=25,
            language_filter=request.language,
        )
        final_results = reciprocal_rank_fusion(
            lex_results,
            sem_scores,
            index.chunks,
            k=config.RRF_K,
            top_k=request.top_k,
        )
    else:
        final_results = lex_results[:request.top_k]

    # Step 4: Query Trace Mermaid diagram
    trace_mermaid = generate_query_trace_mermaid(request.query, norm_terms, final_results)

    return SearchResponse(
        session_id=request.session_id,
        query=request.query,
        normalized_query_terms=norm_terms,
        rewritten_query=rewritten_query,
        mode=request.mode if (request.mode == "lexical" or is_semantic_available()) else "lexical (fallback)",
        total_results=len(final_results),
        results=final_results,
        query_trace_mermaid=trace_mermaid,
    )


@app.post("/api/explain", response_model=ExplainResponse)
def explain(request: ExplainRequest):
    """Generate a strictly grounded AI explanation citing only verified evidence items."""
    index = get_or_load_index(request.session_id)
    if not index:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Retrieve selected chunk results
    selected_results = []
    for rank_idx, cid in enumerate(request.result_ids, 1):
        chunk = index.chunks.get(cid)
        if chunk:
            from src.backend.models import ScoreBreakdown, SearchResult
            selected_results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    evidence_id=f"E{rank_idx}",
                    path=chunk.path,
                    language=chunk.language,
                    kind=chunk.kind,
                    symbol=chunk.symbol,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    code=chunk.code,
                    docstring=chunk.docstring,
                    score=1.0,
                    breakdown=ScoreBreakdown(),
                )
            )

    return generate_grounded_explanation(request.query, selected_results)


@app.get("/api/graph/{session_id}", response_model=GraphResponse)
def get_graph(
    session_id: str,
    focus: Optional[str] = Query(None, description="Focus on a specific file and its dependencies"),
    highlights: Optional[str] = Query(None, description="Comma-separated files to highlight"),
):
    """Retrieve file-to-file dependency graph formatted as Mermaid markup."""
    index = get_or_load_index(session_id)
    if not index:
        raise HTTPException(status_code=404, detail="Session not found.")

    highlight_list = [h.strip() for h in highlights.split(",") if h.strip()] if highlights else None
    mermaid_str, node_c, edge_c, is_truncated = build_dependency_graph(
        list(index.chunks.values()),
        max_nodes=40,
        focus_file=focus,
        highlight_files=highlight_list,
    )

    return GraphResponse(
        mermaid=mermaid_str,
        node_count=node_c,
        edge_count=edge_c,
        truncated=is_truncated,
    )


@app.get("/api/index/{session_id}/terms", response_model=TermPosting)
def inspect_term(session_id: str, q: str = Query(..., description="Term to look up in inverted index")):
    """Inspect posting list and document frequencies for an indexed term."""
    index = get_or_load_index(session_id)
    if not index:
        raise HTTPException(status_code=404, detail="Session not found.")

    return index.get_term_postings(q)


@app.get("/api/file", response_model=FileContextResponse)
def get_file_context(
    session_id: str = Query(...),
    path: str = Query(...),
    start: int = Query(1, ge=1),
    end: int = Query(1, ge=1),
    context: int = Query(10, ge=0, le=50),
):
    """Retrieve context lines around a code snippet with strict path traversal checks."""
    session_dir = (config.DATA_DIR / session_id / "raw").resolve()
    target_file = (session_dir / path).resolve()

    try:
        target_file.relative_to(session_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail="Path traversal forbidden.")

    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        content = target_file.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot read file: {e}")

    lines = content.splitlines()
    total_lines = len(lines)

    c_start = max(1, start - context)
    c_end = min(total_lines, end + context)
    slice_lines = lines[c_start - 1 : c_end]

    return FileContextResponse(
        path=path,
        total_lines=total_lines,
        start_line=c_start,
        end_line=c_end,
        code="\n".join(slice_lines),
        highlight_start=start,
        highlight_end=end,
    )


@app.post("/api/eval/run")
def run_eval_endpoint(session_id: str = Query("sample_repo")):
    """Run retrieval evaluation suite on the session against verified questions."""
    index = get_or_load_index(session_id)
    if not index:
        raise HTTPException(status_code=404, detail="Session index not found.")

    questions_file = config.BASE_DIR / "tests" / "eval_questions.json"
    if not questions_file.exists():
        raise HTTPException(status_code=404, detail="eval_questions.json not found.")

    import json
    with open(questions_file, "r", encoding="utf-8") as f:
        eval_questions = json.load(f)

    results = run_evaluation(eval_questions, index, top_k=10)
    save_eval_results_to_docs(results)
    return results


# Mount frontend static files
DOCS_DIR = config.BASE_DIR / "docs"
if DOCS_DIR.exists():
    app.mount("/docs", StaticFiles(directory=str(DOCS_DIR)), name="docs")

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def index_page():
        response = FileResponse(str(FRONTEND_DIR / "index.html"))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
