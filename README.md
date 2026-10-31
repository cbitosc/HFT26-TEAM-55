# CodeCompass 🧭
> **Problem Statement**: Helping New Contributors Find the Right Code

CodeCompass is an intelligent developer onboarding assistant designed to help new contributors explore, navigate, and comprehend unfamiliar codebases in seconds. It combines defensive in-memory archive ingestion, Python AST symbol extraction, local-first SQLite FTS5 search with BM25 ranking, and contextual AI onboarding explanations powered by Featherless AI (`Qwen/Qwen2.5-7B-Instruct`).

---

## 🏗️ Architecture & Pipeline Overview

```
   ┌─────────────────────────────────────────────────────────────┐
   │                     1. ZIP Ingestion                        │
   │  - Defensive validation (20 MiB archive, 100 MiB bomb check)│
   │  - Path traversal, symlink & encryption protection          │
   │  - In-memory stream processing (never writes unvetted files)│
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                     2. AST Parsing                          │
   │  - Extracts functions, methods, async functions & classes   │
   │  - Preserves exact line numbers & parent scope hierarchy    │
   │  - Isolate code snippets & docstrings                       │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                  3. SQLite FTS5 Indexing                    │
   │  - Relational tables: repositories, files, symbols          │
   │  - FTS5 Virtual Table: code_search_fts (unicode61)          │
   │  - Atomic repository replacement with foreign key cascading │
   │  - BM25 relevance ranking: symbol_name, content, docstring  │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │             4. Featherless AI Code Explanation              │
   │  - Authoritative SQLite metadata lookup via symbol_id       │
   │  - Anti-injection defense: code treated as untrusted data   │
   │  - Strict grounding: cites exact file path & line ranges    │
   │  - Model: Qwen/Qwen2.5-7B-Instruct (Zero Key Leaks)         │
   └─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Custom Midnight Navy Theme & Parallax Architecture
- **Backend**: Python 3.13, FastAPI, Uvicorn, Python-dotenv
- **Database**: SQLite 3 with FTS5 Full-Text Search Virtual Tables & BM25 Ranking
- **AI Service**: Featherless AI (`Qwen/Qwen2.5-7B-Instruct`)
- **Security**: In-memory ZIP validator, prompt injection shields, safe tokenized React rendering (zero `dangerouslySetInnerHTML`)

---

## 📁 Project Structure

```text
Antigravity/
├── .gitignore                   # Root gitignore (OS files, node_modules, .db, .env)
├── README.md                    # Project documentation & setup guide
├── backend/
│   ├── .gitignore               # Python venv, SQLite db, and secrets ignore
│   ├── .env.example             # Template environment variables (Qwen 2.5)
│   ├── requirements.txt         # FastAPI, Uvicorn, python-multipart, python-dotenv
│   ├── app/
│   │   ├── __init__.py          # App package initialization
│   │   ├── config.py            # Central configuration loader
│   │   ├── main.py              # FastAPI entrypoint with lifespan DB init & CORS
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py      # SQLite connection context & schema initialization
│   │   │   └── schema.py        # Relational tables & FTS5 virtual table DDL
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── repository.py    # /api/repository/upload & /api/repository/status
│   │   │   ├── search.py        # /api/search (BM25 full-text query)
│   │   │   └── ai.py            # /api/ai/explain & /api/ai/status
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── zip_validator.py # Defensive archive validator & bomb protector
│   │       ├── ast_parser.py    # Fault-tolerant Python AST symbol visitor
│   │       ├── indexer.py       # Atomic SQLite & FTS5 indexing service
│   │       ├── search_service.py# BM25 parameterized FTS5 search service
│   │       └── ai_service.py    # Featherless AI client with prompt injection guard
│   └── tests/
│       ├── __init__.py
│       ├── test_stage5.py       # 10 tests: Indexing, BM25, atomic replacement, rollback
│       ├── test_stage6_ai.py    # 12 tests: Mocked AI, prompt defense, grounding, timeouts
│       └── verify_e2e_workflow.py # End-to-end integration test runner
└── frontend/
    ├── .gitignore               # Node dependencies and build artifacts ignore
    ├── package.json             # React, TypeScript, and Vite dependencies
    ├── tsconfig.json            # Strict TypeScript configuration
    ├── vite.config.ts           # Development proxy (/api -> http://127.0.0.1:8000)
    └── src/
        ├── App.tsx              # Application shell & state coordinator
        ├── App.css              # Midnight Navy design system & component styles
        ├── index.css            # Base typography, resets & theme tokens
        ├── types/
        │   └── navigation.ts    # TypeScript interfaces for search, upload, and AI
        └── components/
            ├── ArchitectureGrid.tsx   # System architecture overview cards
            ├── BackendStatusBadge.tsx # Real-time backend connectivity badge
            ├── GeometricBackground.tsx# Cinematic floating geometry & parallax
            ├── RepoUploadZone.tsx     # Drag-and-drop archive upload zone
            ├── SearchBar.tsx          # Natural language search bar with Cmd+K
            ├── Sidebar.tsx            # Navigation drawer & metadata sidebar
            ├── WelcomeHero.tsx        # Developer onboarding hero banner
            ├── SafeHighlight.tsx      # Tokenizer for safe FTS5 <mark> rendering
            ├── SafeMarkdown.tsx       # Pure React safe Markdown renderer (No XSS)
            ├── AIExplanationPanel.tsx # Independent on-demand AI explanation panel
            └── views/
                ├── OverviewView.tsx   # Welcome, search preview, upload & architecture
                ├── RepositoryView.tsx # Archive upload, indexing progress & active repo
                ├── SearchView.tsx     # Real code search results & AI explanation
                └── SettingsView.tsx   # Diagnostics, storage & AI provider status
```

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.13+ (`py -3.13` or `python`)
- Node.js (v18+) and npm

---

### 1. Backend Setup

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   - **Windows PowerShell**:
     ```powershell
     py -3.13 -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   copy .env.example .env     # Windows
   cp .env.example .env       # Linux / macOS
   ```
   *Edit `.env` to configure your `FEATHERLESS_API_KEY`.*

5. Start the FastAPI backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   - API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - Health Check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

### 2. Frontend Setup

1. Open a second terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

4. Open your browser at [http://localhost:5173](http://localhost:5173).

---

## 🧪 Running Automated Tests

All tests run in standard Python `unittest` without external test dependencies and use **100% mocked responses for AI calls**, ensuring zero credit consumption:

```bash
# From the project root:
backend\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```

Test coverage includes:
- **Defensive ZIP Extraction**: 20MB archive limit, 100MB bomb protection, path traversal defenses.
- **AST Parsing**: Scope-aware visitor, line numbers, snippets, docstrings, syntax error fault tolerance.
- **SQLite FTS5 Search**: Relational tables, BM25 scoring, prefix tokenization, empty query handling.
- **Atomic Replacement & ACID Rollback**: Relational foreign key cascading, FTS purge, transaction rollback.
- **Featherless AI Explanations**: Authoritative DB lookup, prompt injection protection, grounded line citing, payload isolation, timeouts, HTTP errors (401, 429, 503), malformed JSON handling.

---

## 🛡️ Security & Guardrails

1. **In-Memory Defensive Processing**: ZIP archives are validated and extracted strictly in memory. Any attempt at path traversal (`..`, `:`, `/`, null bytes), symlinks, or zip bombs is rejected before disk write.
2. **Zero Client Trust for AI**: The frontend transmits only `symbol_id` and optional query context. The backend retrieves the code snippet, file path, and line bounds directly from the verified SQLite database.
3. **Prompt Injection Defense**: Repository code, docstrings, and user queries are treated as passive untrusted data. System directives explicitly forbid the model from executing code instructions or revealing secrets.
4. **Secret Isolation**: `FEATHERLESS_API_KEY` is loaded in the backend only. It is never logged, never returned in API responses, and stripped from error messages.
5. **Zero `dangerouslySetInnerHTML`**: All code snippets, FTS5 `<mark>` highlights, and model-generated Markdown are rendered as escaped React text nodes.
