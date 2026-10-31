"""Database schema definitions for CodeCompass SQLite and FTS5 search."""

SCHEMA_SQL = """
-- Repositories metadata table
CREATE TABLE IF NOT EXISTS repositories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    total_files INTEGER NOT NULL DEFAULT 0,
    total_symbols INTEGER NOT NULL DEFAULT 0,
    total_lines INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
);

-- Files table
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id TEXT NOT NULL,
    path TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'python',
    size_bytes INTEGER NOT NULL,
    line_count INTEGER NOT NULL,
    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
    UNIQUE (repository_id, path)
);

-- Symbols table
CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    repository_id TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    parent_scope TEXT,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    docstring TEXT,
    snippet TEXT NOT NULL,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
);

-- Relational indexes
CREATE INDEX IF NOT EXISTS idx_files_repo ON files(repository_id);
CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id);
CREATE INDEX IF NOT EXISTS idx_symbols_repo ON symbols(repository_id);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);

-- SQLite FTS5 Virtual Table for full-text code search
CREATE VIRTUAL TABLE IF NOT EXISTS code_search_fts USING fts5(
    symbol_name,
    file_path,
    parent_scope,
    docstring,
    content,
    symbol_id UNINDEXED,
    file_id UNINDEXED,
    repository_id UNINDEXED,
    start_line UNINDEXED,
    end_line UNINDEXED,
    kind UNINDEXED,
    tokenize = 'unicode61'
);
"""
