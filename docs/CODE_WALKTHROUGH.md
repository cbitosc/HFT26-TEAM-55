# NextGen Code Explorer — Code Walkthrough

This document provides a module-by-module walkthrough of the NextGen Code Explorer codebase, explaining key functions, data structures, and a complete worked example of how a query moves through the retrieval pipeline.

---

## 1. Directory Structure

```text
src/
  backend/
    config.py           # Configurable thresholds, limits, weights, and environment variables
    models.py           # Pydantic schemas for chunks, searches, citations, and breakdowns
    ingest.py           # Safe ZIP extraction, Zip-Slip defense, and file exclusion filtering
    parsers/
      __init__.py       # Language dispatcher based on file extension
      python_parser.py  # Python ast extraction of functions, classes, and line numbers
      js_ts_parser.py   # Regex + brace-matching parser for JS/TS/Java
      markdown_parser.py# Section chunker by Markdown headings (#, ##)
    tokenizer.py        # Code-aware tokenization, identifier splitting, stemming
    inverted_index.py   # Handcrafted field-aware inverted index with JSON disk persistence
    ranker.py           # BM25F multi-field scoring and explainable boost engine
    semantic.py         # Optional all-MiniLM-L6-v2 embeddings loader & cosine similarity
    fusion.py           # Reciprocal Rank Fusion (k=60) combining lexical and semantic ranks
    graph.py            # File dependency resolution and Mermaid flowchart generator
    llm.py              # Featherless AI client, query expansion, strict citation validator
    evaluation.py       # Benchmark evaluation engine (Hit@1, Hit@3, MRR)
    app.py              # FastAPI application server, REST routes, static file mounting
  frontend/
    index.html          # Semantic single-page dashboard with tabs, results, and modals
    styles.css          # Responsive design, light/dark themes, distinct purple & green cards
    app.js              # Vanilla JS controller: API calls, Mermaid rendering, citations
docs/
  architecture.md       # High-level architecture and sequence diagrams
  CODE_WALKTHROUGH.md   # This comprehensive architectural walkthrough
  eval_results.json     # Saved benchmark results from automated evaluation
tests/
  sample_repo/          # Bundled 18-file Python+JS e-commerce platform (ShopStream)
  eval_questions.json   # 14 verified benchmark questions with ground truth
  run_eval.py           # Command-line benchmark harness
  test_*.py             # Unit tests for tokenizer, ingest, parsers, index, fusion, llm
```

---

## 2. Module Breakdown

### `src/backend/config.py`
- **Purpose**: Defines configuration limits, file exclusions, scoring weights, and environment variables loaded via `python-dotenv`.
- **Key Settings**:
  - `MAX_ZIP_SIZE_MB = 50`: Upper bound for uploaded archive size.
  - `MAX_UNCOMPRESSED_SIZE_MB = 200`: Maximum decompressed byte limit.
  - `MAX_SINGLE_FILE_BYTES = 204800` (200 KB): Single file cutoff.
  - `EXCLUDED_DIRS`: Skips `node_modules`, `.git`, `venv`, `__pycache__`, `dist`, `build`, etc.
  - `WEIGHT_SYMBOL = 3.0, WEIGHT_PATH = 2.0, WEIGHT_DOCSTRING = 1.5, WEIGHT_CODE = 1.0`: Configurable BM25F field weights.

### `src/backend/models.py`
- **Purpose**: Pydantic data contracts ensuring strict typing between backend subsystems and frontend API clients.
- **Key Schemas**:
  - `CodeChunk`: Unit of indexed code (`id`, `path`, `language`, `kind`, `symbol`, `start_line`, `end_line`, `code`, `docstring`, `imports`).
  - `ScoreBreakdown`: Explainability payload detailing matched terms, field contributions, applied boosts, and rank comparisons.
  - `SearchResult`: Evidence item displaying real code and line ranges, assigned an evidence ID like `[E1]`.
  - `Citation`: Validated reference mapping an evidence ID back to file path and exact lines.

### `src/backend/ingest.py`
- **Purpose**: Safe archive ingestion and deterministic file filtering.
- **Key Functions**:
  - `validate_zip_safety(zf)`: Scans ZipInfo entries before extraction. Throws `IngestionError` if any path contains `..`, leading slashes, symlinks, or suspicious compression ratios (>100:1).
  - `extract_zip_safely(bytes, target_dir)`: Extracts verified files and automatically strips single wrapper directories so relative paths remain natural.
  - `should_index_file(rel_path, abs_path)`: Filters out dependency folders, minified scripts (`*.min.js`), sourcemaps (`*.map`), lockfiles, images, binaries, and oversized files.
  - `scan_repository(repo_dir)`: Returns accepted files and exact skipped counts by category.

### `src/backend/parsers/`
- **`python_parser.py`**:
  - Uses Python's built-in `ast` module (`ast.parse()`, `ast.walk()`, `ast.FunctionDef`, `ast.ClassDef`).
  - Extracts exact start and end line numbers (`node.lineno`, `node.end_lineno`), docstrings, parent classes, and import statements.
  - Splits oversized chunks (>120 lines) into overlapping windows to keep evidence snippets digestible.
  - Falls back to line-based windowing on `SyntaxError`.
- **`js_ts_parser.py`**:
  - Regular expression patterns detect `function`, arrow functions (`const x = () => {}`), `class`, and Java method headers.
  - `find_matching_brace(code, start_idx)` matches nested braces across strings and comments to determine accurate line numbers.
- **`markdown_parser.py`**:
  - Splits Markdown files by section headings (`#`, `##`, `###`) so documentation can be retrieved for conceptual queries.

### `src/backend/tokenizer.py`
- **Purpose**: Code-aware lexical normalization and identifier splitting.
- **Key Functions**:
  - `split_identifier(name)`: Splits camelCase (`saveUploadedFile` -> `['save', 'uploaded', 'file']`), snake_case (`login_user` -> `['login', 'user']`), and digits (`v2` -> `['v2', 'v', '2']`).
  - `stem_token(word)`: Deterministic light suffix stemming (`repositories` -> `repository`, `filtering` -> `filter`, `extracted` -> `extract`).
  - `tokenize(text, remove_stopwords)`: Produces a normalized token stream. Removes conversational filler words (`where`, `is`, `handled`, `the`) for queries.

### `src/backend/inverted_index.py`
- **Purpose**: Handcrafted in-memory and disk-persisted field-aware inverted index.
- **Data Structures**:
  - `postings[field][term] = {chunk_id: {"tf": int, "positions": [int]}}`
  - `doc_lengths[field][chunk_id] = int`
  - `avg_doc_len[field] = float`
  - `doc_freq[term] = int` (count of chunks containing term)
- **Key Functions**:
  - `add_chunk(chunk)`: Indexes code across `symbol`, `path`, `docstring`, and `code`.
  - `compute_idf(term)`: Computes $IDF(t) = \ln\left(1 + \frac{N - n_t + 0.5}{n_t + 0.5}\right)$.
  - `save_to_disk()` / `load_from_disk()`: Persists index to `inverted_index.json` so state survives server restarts.

### `src/backend/ranker.py`
- **Purpose**: BM25F multi-field scoring and explainable boost engine.
- **Scoring Details**:
  - Normalizes term frequency per field: $norm\_tf(t, d, f) = \frac{tf(t, d, f)}{1 - b + b \cdot \frac{len(d, f)}{avg\_len(f)}}$.
  - Computes weighted contribution: $\tilde{tf}(t, d) = \sum_f w_f \cdot norm\_tf(t, d, f)$.
  - BM25 saturation: $Score(t, d) = IDF(t) \cdot \frac{\tilde{tf}(t, d) \cdot (k_1 + 1)}{\tilde{tf}(t, d) + k_1}$.
  - Applies explainable boosts:
    - **Exact Symbol Match** (+4.0)
    - **Symbol Component Match** (+3.0)
    - **Path Match** (+2.5)
    - **Documentation Intent** (+2.0)
  - Constructs `ScoreBreakdown` detailing why each candidate ranked where it did.

### `src/backend/semantic.py` & `src/backend/fusion.py`
- **`semantic.py`**:
  - Lazy-loads `sentence-transformers` with `all-MiniLM-L6-v2`.
  - If the package is not installed, gracefully returns `is_semantic_available() == False` without breaking.
  - Caches chunk embeddings to `embeddings.json` on disk.
- **`fusion.py`**:
  - Reciprocal Rank Fusion: $RRF(d) = \sum_{m} \frac{1}{k + rank_m(d)}$ with $k = 60$.
  - Fuses lexical results with semantic similarity rankings.

### `src/backend/graph.py`
- **Purpose**: Synthesizes file dependency graphs and query trace flowcharts formatted as Mermaid markup.
- **Key Functions**:
  - `build_dependency_graph(chunks, max_nodes=40)`: Resolves internal Python and JS imports to indexed files, sanitizes node IDs, and formats Mermaid flowchart syntax.
  - `generate_query_trace_mermaid(query, terms, results)`: Generates real-time query execution flowchart: `Query -> Normalized Terms -> Postings Lists -> Candidates -> Top Result`.

### `src/backend/llm.py`
- **Purpose**: Featherless AI integration adhering to strict factual grounding.
- **Key Functions**:
  - `generate_grounded_explanation(query, results)`: Transmits **ONLY** the top retrieved evidence blocks (`[E1] auth/login.py:10-25`) to Meta-Llama-3.1-8B-Instruct.
  - `validate_citations_and_claims(text, evidence_map)`: Uses regex `\[(E\d+)\]` to verify every cited ID against existing evidence. Automatically strips hallucinated or unverified citation tokens.
  - Never logs or exposes API keys. Fails gracefully to search-only mode if no key is present.

### `src/backend/app.py`
- **Purpose**: FastAPI routing, asynchronous background indexing tasks, security checks, and static file serving.
- **Key Endpoints**:
  - `POST /api/upload`: Safely handles ZIP uploads and triggers background indexing.
  - `POST /api/sample`: Loads the bundled ShopStream project for fast evaluation.
  - `GET /api/status/{session_id}`: Polls progress and skipped file statistics.
  - `POST /api/search`: Executes lexical or hybrid search and returns evidence with query trace.
  - `POST /api/explain`: Returns grounded AI explanation with validated citations.
  - `GET /api/graph/{session_id}`: Returns Mermaid dependency flowchart.
  - `GET /api/index/{session_id}/terms?q=...`: Inspects inverted index posting lists.
  - `GET /api/file`: Returns source file context lines with strict path traversal checks.
  - `POST /api/eval/run`: Runs the 14-question benchmark suite.

---

## 3. Worked Example: Tracing a Query

Let's trace the query **`"where is login handled?"`** through the system:

1. **User Input**:
   The user types `"where is login handled?"` into the dashboard search bar.
2. **Tokenization (`tokenizer.py`)**:
   - `tokenize(query, remove_stopwords=True)` removes conversational filler words (`where`, `is`, `handled`).
   - Suffix stemming evaluates remaining terms: `'login'`.
   - Resulting search terms: `['login']`.
3. **Posting List Lookup (`inverted_index.py`)**:
   - The inverted index queries `postings[field]['login']` across `symbol`, `path`, `docstring`, and `code`.
   - Matches candidate chunks:
     - `auth/login.py:login_user:L15-L30` (matched in `symbol`, `path`, `docstring`, `code`).
     - `api/routes.py:handle_login:L12-L24` (matched in `symbol`, `code`).
4. **BM25F Field Weighting (`ranker.py`)**:
   - In `auth/login.py`, `'login'` appears in `symbol` ($w=3.0$), `path` ($w=2.0$), and `code` ($w=1.0$).
   - Document lengths are normalized against average field lengths.
   - Lucene IDF for `'login'` is calculated based on repository frequency: $IDF \approx 2.45$.
   - Raw BM25F score: $1.42$.
5. **Boost Application (`ranker.py`)**:
   - `login_user` contains the query term in its symbol name: **Symbol Match Boost (+3.0)**.
   - The file path `auth/login.py` contains `'login'`: **Path Match Boost (+2.5)**.
   - Final lexical score: $1.42 + 3.0 + 2.5 = 6.92$.
6. **Ranking & Evidence Tagging**:
   - `auth/login.py` ranks #1 and is assigned evidence ID **`[E1]`**.
   - `api/routes.py` ranks #2 and is assigned evidence ID **`[E2]`**.
7. **Grounded AI Explanation (`llm.py`)**:
   - The backend prepares evidence block:
     ```text
     [E1] auth/login.py:15-30 (login_user)
     def login_user(email: str, password: str):
         ...
     ```
   - Featherless (Llama-3.1) receives this snippet and responds:
     > "User authentication is handled by `login_user` in `auth/login.py`, which validates credentials and generates a JWT session token. [E1]"
   - The citation validator confirms `[E1]` exists and creates a clickable link.
8. **UI Presentation**:
   - The dashboard displays the purple **AI-Generated Explanation** at the top with clickable `[E1]`.
   - The green **Verified Source Evidence** card below displays the exact lines of `auth/login.py` with syntax highlighting and line numbers.
   - Clicking `[E1]` smoothly scrolls to and highlights the evidence card.
