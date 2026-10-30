# NextGen Code Explorer — System Architecture

NextGen Code Explorer is a local-first code discovery engine designed to help new open-source contributors find exact files, functions, and lines in unfamiliar repositories with mathematically verifiable ranking and strictly grounded AI explanations.

---

## 1. High-Level System Architecture

```mermaid
flowchart TD
    User["Developer / Contributor"]
    UI["Single-Page Dashboard<br/>(HTML5 / CSS3 / Vanilla JS)"]
    API["FastAPI Application Server<br/>(Uvicorn loopback)"]

    subgraph Ingestion["Safe Ingestion Pipeline"]
        ZipCheck["ZIP Safety & Zip-Slip Defense"]
        Filter["Deterministic File Filter<br/>(Excludes node_modules, .git, venv, binaries)"]
        RawDir[("Local Session Storage<br/>data/sessions/<id>/raw")]
    end

    subgraph Parsing["Semantic Chunking"]
        PyAST["Python ast Parser<br/>(Exact line numbers, classes, functions)"]
        JSParse["JS / TS / Java Parser<br/>(Regex + Brace Matcher)"]
        MDParse["Markdown Section Chunker"]
    end

    subgraph Indexing["Handcrafted Retrieval Engine"]
        Tok["Code-Aware Tokenizer<br/>(camelCase, snake_case, stemming)"]
        InvIndex[("Field-Aware Inverted Index<br/>(symbol, path, docstring, code)")]
        BM25F["BM25F Scoring & Boosting"]
        Embeddings["Optional all-MiniLM-L6-v2 Embeddings"]
        RRF["Reciprocal Rank Fusion (k=60)"]
    end

    subgraph Visuals["Mermaid Graph Engine"]
        DepGraph["Dependency Graph Resolver"]
        TraceGraph["Query Trace Flowchart"]
    end

    subgraph AILayer["Grounded AI Verification"]
        Featherless["Featherless API<br/>(Meta-Llama-3.1-8B-Instruct)"]
        Validator["Strict Citation Validator<br/>(Strips hallucinated [E#] IDs)"]
    end

    User -->|"Upload ZIP / Query"| UI
    UI -->|"REST Endpoints"| API
    API --> ZipCheck --> Filter --> RawDir
    RawDir --> PyAST & JSParse & MDParse
    PyAST & JSParse & MDParse --> Tok --> InvIndex
    InvIndex --> BM25F
    BM25F & Embeddings --> RRF
    RRF -->|"Verified Evidence [E1..En]"| UI
    RRF -->|"Top Evidence Blocks Only"| Featherless
    Featherless --> Validator -->|"Grounded Explanation"| UI
    Parsing --> DepGraph --> UI
    BM25F --> TraceGraph --> UI
```

---

## 2. End-to-End Workflow Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Contributor
    participant UI as Dashboard UI
    participant API as FastAPI Backend
    participant Ingest as Ingestion & Parsers
    participant Index as Inverted Index & RRF
    participant LLM as Featherless AI (Llama 3.1)

    Dev->>UI: Upload repository ZIP archive
    UI->>API: POST /api/upload
    API->>Ingest: Validate archive (Zip-Slip defense, compression limits)
    Ingest->>Ingest: Filter out build/dep directories (.git, node_modules)
    Ingest->>Ingest: Extract AST functions, classes, line numbers
    Ingest->>Index: Build field-aware inverted index & save to disk
    API-->>UI: Indexing ready (stats: files, symbols, unique terms)

    Dev->>UI: Ask: "where is login handled?"
    UI->>API: POST /api/search (query, mode="hybrid")
    API->>Index: Tokenize query -> split camel/snake -> stem
    Index->>Index: BM25F scoring across symbol, path, docstring, code
    Index->>Index: Apply symbol & path boosts
    Index->>Index: Reciprocal Rank Fusion (k=60)
    API-->>UI: Return ranked results [E1, E2, ...] + Query trace Mermaid

    UI->>API: POST /api/explain (query, [E1, E2, ...])
    API->>LLM: Send ONLY evidence blocks ([E1] auth/login.py:10-25)
    LLM-->>API: Response with citations ("[E1]")
    API->>API: Validate & strip any non-existent citations
    API-->>UI: Display Grounded Explanation + Clickable [E1] links
    Dev->>UI: Click [E1] to highlight exact source code & line numbers
```

---

## 3. Core Architectural Guarantees

1. **Strictly Grounded Explanations**: The AI model is NEVER sent the entire repository. It only receives the top retrieved code snippets formatted as numbered evidence blocks (`[E1]`, `[E2]`). The backend rigorously parses and validates every citation tag (`\[E\d+\]`) against genuine evidence IDs, stripping hallucinated references.
2. **Zero Hallucination Search**: Retrieval is powered by a handcrafted, deterministic, field-aware BM25F inverted index. No black-box AI model decides which files exist or which functions match.
3. **Zip-Slip & Path Traversal Immunity**: Archive extraction enforces strict canonical path containment (`os.path.commonpath`), disallows symbolic links, and validates compression ratios to prevent zip bombs. File context viewing (`/api/file`) enforces containment inside the session directory.
4. **Complete Offline / Search-Only Resilience**: If no Featherless API key is provided, or if the network is disconnected, search functions with 100% fidelity. The UI clearly reports the operational status of the AI and semantic layers.
