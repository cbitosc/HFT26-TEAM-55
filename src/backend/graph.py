"""Dependency graph construction and Mermaid diagram generation for NextGen Code Explorer."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.backend.models import CodeChunk, SearchResult


def sanitize_mermaid_id(name: str) -> str:
    """Create a safe alphanumeric node identifier for Mermaid."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if not clean or clean[0].isdigit():
        clean = "node_" + clean
    return clean


def sanitize_mermaid_label(label: str) -> str:
    """Escape quotes and brackets in labels so Mermaid never syntax errors."""
    safe = label.replace('"', "'").replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    return safe


def resolve_import_to_file(
    source_path: str,
    import_stmt: str,
    indexed_files: Set[str],
) -> Optional[str]:
    """Resolve an import string to a relative file path within the indexed repository."""
    # Strip dots and split
    clean_import = import_stmt.strip()

    # 1. Direct match or with extensions
    for ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".java"]:
        candidate = f"{clean_import}{ext}"
        if candidate in indexed_files:
            return candidate

    # 2. Python module notation: 'auth.token' -> 'auth/token.py' or 'auth/token/__init__.py'
    py_path = clean_import.replace(".", "/")
    for ext in [".py", "/__init__.py"]:
        candidate = f"{py_path}{ext}"
        if candidate in indexed_files:
            return candidate

    # 3. Relative JS/TS imports: './utils' or '../config'
    if clean_import.startswith("."):
        source_dir = Path(source_path).parent
        resolved = (source_dir / clean_import).resolve()
        # Find relative to source_dir's root
        # Check against indexed_files
        for indexed in indexed_files:
            indexed_p = Path(indexed)
            if indexed_p.name.startswith(Path(clean_import).name):
                return indexed

    # 4. Check if any indexed file ends with this module name
    target_name = clean_import.split(".")[-1]
    for indexed in indexed_files:
        p = Path(indexed)
        if p.stem == target_name and p.suffix in [".py", ".js", ".ts"]:
            return indexed

    return None


def build_dependency_graph(
    chunks: List[CodeChunk],
    max_nodes: int = 40,
    focus_file: Optional[str] = None,
    highlight_files: Optional[List[str]] = None,
) -> Tuple[str, int, int, bool]:
    """Build file-to-file dependency graph and output valid Mermaid flowchart markup.

    Returns:
        (mermaid_string, node_count, edge_count, is_truncated)
    """
    indexed_files: Set[str] = {c.path for c in chunks}
    file_imports: Dict[str, Set[str]] = {}

    for chunk in chunks:
        if chunk.path not in file_imports:
            file_imports[chunk.path] = set()
        for imp in chunk.imports:
            resolved = resolve_import_to_file(chunk.path, imp, indexed_files)
            if resolved and resolved != chunk.path:
                file_imports[chunk.path].add(resolved)

    # All unique edges: (src, dst)
    edges: Set[Tuple[str, str]] = set()
    node_degrees: Dict[str, int] = {f: 0 for f in indexed_files}

    for src, dsts in file_imports.items():
        for dst in dsts:
            edges.add((src, dst))
            node_degrees[src] = node_degrees.get(src, 0) + 1
            node_degrees[dst] = node_degrees.get(dst, 0) + 1

    # Filter/Focus
    selected_nodes: Set[str] = set()
    truncated = False

    if focus_file and focus_file in indexed_files:
        selected_nodes.add(focus_file)
        # Add 1st degree neighbors
        for src, dst in edges:
            if src == focus_file:
                selected_nodes.add(dst)
            if dst == focus_file:
                selected_nodes.add(src)
    else:
        # Pick top nodes by degree
        sorted_nodes = sorted(node_degrees.keys(), key=lambda n: node_degrees[n], reverse=True)
        if len(sorted_nodes) > max_nodes:
            selected_nodes = set(sorted_nodes[:max_nodes])
            truncated = True
        else:
            selected_nodes = set(sorted_nodes)

    filtered_edges = [(s, d) for s, d in edges if s in selected_nodes and d in selected_nodes]

    # Generate Mermaid markup
    lines: List[str] = ["graph TD"]
    highlights = set(highlight_files or [])

    # Define nodes
    for node in sorted(selected_nodes):
        nid = sanitize_mermaid_id(node)
        nlabel = sanitize_mermaid_label(node)
        lines.append(f'  {nid}["{nlabel}"]')

        if node in highlights:
            lines.append(f"  style {nid} fill:#bbf7d0,stroke:#16a34a,stroke-width:2px")
        elif focus_file and node == focus_file:
            lines.append(f"  style {nid} fill:#fed7aa,stroke:#ea580c,stroke-width:3px")

    # Define edges
    for src, dst in sorted(filtered_edges):
        sid = sanitize_mermaid_id(src)
        did = sanitize_mermaid_id(dst)
        lines.append(f"  {sid} --> {did}")

    if not selected_nodes:
        lines.append('  empty["No dependencies found in project"]')

    return "\n".join(lines), len(selected_nodes), len(filtered_edges), truncated


def generate_query_trace_mermaid(
    raw_query: str,
    normalized_terms: List[str],
    matched_results: List[SearchResult],
) -> str:
    """Generate an explainable Mermaid flowchart illustrating the exact query execution trace."""
    clean_q = sanitize_mermaid_label(raw_query[:50])
    lines = ["graph LR"]
    lines.append(f'  Q["Query: \\"{clean_q}\\""]')

    # Terms node
    terms_preview = ", ".join(f"'{t}'" for t in normalized_terms[:4])
    if len(normalized_terms) > 4:
        terms_preview += f" (+{len(normalized_terms) - 4} more)"
    lines.append(f'  T["Normalized Terms:<br/>{sanitize_mermaid_label(terms_preview)}"]')
    lines.append("  Q --> T")

    # Postings node
    lines.append('  PL["Inverted Index Postings<br/>(symbol, path, doc, code)"]')
    lines.append("  T --> PL")

    # BM25F & Boosting
    lines.append('  Rank["BM25F Scoring<br/>+ Symbol/Path Boosts"]')
    lines.append("  PL --> Rank")

    # Top results
    if matched_results:
        top_c = matched_results[0]
        top_label = f"Top: {top_c.evidence_id} - {top_c.symbol or top_c.path}"
        lines.append(f'  Top["{sanitize_mermaid_label(top_label)}<br/>Score: {top_c.score:.2f}"]')
        lines.append("  Rank --> Top")
        lines.append("  style Top fill:#bbf7d0,stroke:#16a34a,stroke-width:2px")
    else:
        lines.append('  NoRes["No Matches Found"]')
        lines.append("  Rank --> NoRes")
        lines.append("  style NoRes fill:#fee2e2,stroke:#ef4444")

    return "\n".join(lines)
