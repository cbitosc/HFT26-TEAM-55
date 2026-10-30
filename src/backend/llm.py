"""Featherless AI integration for query rewrite, grounded explanation, and strict citation verification."""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional, Set, Tuple

from src.backend import config
from src.backend.models import Citation, ExplainResponse, SearchResult

_CITATION_REGEX = re.compile(r"\[(E\d+)\]")


def get_client():
    """Create an OpenAI client targeting the Featherless API endpoint."""
    api_key = config.FEATHERLESS_API_KEY or os.getenv("FEATHERLESS_API_KEY", "")
    if not api_key:
        return None

    try:
        from openai import OpenAI
        return OpenAI(
            base_url=config.FEATHERLESS_BASE_URL,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/NextGen-Code-Explorer",
                "X-Title": config.APP_TITLE,
            },
            timeout=25.0,
        )
    except Exception:
        return None


def rewrite_query_with_ai(query: str) -> Optional[List[str]]:
    """Use AI to expand conversational queries into technical code keywords and identifiers.

    Returns:
        List of expanded keywords/identifiers, or None if unavailable/failed.
    """
    client = get_client()
    if not client:
        return None

    prompt = (
        "You are a code search assistant. Given the following developer question, "
        "extract 2 to 6 specific code terms, method names, or identifier candidates "
        "that would appear in the source code.\n"
        f"Question: \"{query}\"\n"
        "Return ONLY a JSON array of strings, e.g.: [\"term1\", \"term2\"]"
    )

    try:
        completion = client.chat.completions.create(
            model=config.FEATHERLESS_MODEL,
            messages=[
                {"role": "system", "content": "You return only JSON arrays."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=100,
        )
        content = completion.choices[0].message.content or ""
        # Extract JSON array
        m = re.search(r"\[.*\]", content, re.DOTALL)
        if m:
            terms = json.loads(m.group(0))
            if isinstance(terms, list):
                return [str(t).strip() for t in terms if str(t).strip()]
    except Exception:
        pass

    return None


def format_evidence_blocks(results: List[SearchResult]) -> str:
    """Format retrieved code results into strict numbered evidence blocks."""
    blocks: List[str] = []
    for res in results:
        header = f"[{res.evidence_id}] {res.path}:{res.start_line}-{res.end_line} ({res.symbol or 'module'})"
        code_body = res.code.strip()
        blocks.append(f"{header}\n```\n{code_body}\n```")
    return "\n\n".join(blocks)


def validate_citations_and_claims(
    raw_explanation: str,
    evidence_map: Dict[str, SearchResult],
) -> Tuple[str, List[Citation], List[str]]:
    """Validate citations against evidence.

    Strips fake citations and non-existent evidence IDs.
    Returns:
        (sanitized_explanation, valid_citations, invalid_citations_stripped)
    """
    valid_citations_list: List[Citation] = []
    seen_valid_ids: Set[str] = set()
    invalid_citations: List[str] = []

    def replace_citation(match: re.Match) -> str:
        cid = match.group(1)
        if cid in evidence_map:
            if cid not in seen_valid_ids:
                seen_valid_ids.add(cid)
                res = evidence_map[cid]
                valid_citations_list.append(
                    Citation(
                        evidence_id=cid,
                        path=res.path,
                        start_line=res.start_line,
                        end_line=res.end_line,
                        symbol=res.symbol or res.path,
                    )
                )
            return f"[{cid}]"
        else:
            invalid_citations.append(cid)
            return ""  # Strip hallucinated citation

    sanitized = _CITATION_REGEX.sub(replace_citation, raw_explanation)

    # Clean up double spaces or orphan punctuation from stripped citations
    sanitized = re.sub(r"\s+", " ", sanitized).strip()

    return sanitized, valid_citations_list, invalid_citations


def generate_grounded_explanation(
    query: str,
    results: List[SearchResult],
) -> ExplainResponse:
    """Generate a concise explanation strictly citing provided code evidence."""
    if not results:
        return ExplainResponse(
            explanation="No verified evidence was found for this query.",
            valid_citations=[],
            invalid_citations_stripped=[],
            grounded=True,
            error=None,
        )

    evidence_map = {res.evidence_id: res for res in results}
    client = get_client()

    if not client:
        return ExplainResponse(
            explanation="AI explanation unavailable (FEATHERLESS_API_KEY is not configured). "
                        "Review the verified source evidence cards above.",
            valid_citations=[],
            invalid_citations_stripped=[],
            grounded=True,
            error="FEATHERLESS_API_KEY is not set. Offline mode active.",
        )

    evidence_text = format_evidence_blocks(results)

    system_instruction = (
        "You are a code explorer assistant. Your core guarantee is strict factual grounding.\n"
        "1. You are given a user question and a numbered set of verified source code evidence snippets ([E1], [E2], ...).\n"
        "2. Answer the question using ONLY the provided evidence.\n"
        "3. Every factual claim MUST cite its evidence ID, e.g. [E1] or [E2].\n"
        "4. If the provided snippets do not contain enough information to answer, state clearly: "
        "'The retrieved source evidence does not contain sufficient information to answer this question.'\n"
        "5. NEVER invent file paths, functions, or line numbers outside the provided snippets.\n"
        "6. Keep your explanation concise (2 to 4 sentences)."
    )

    user_prompt = f"Question: {query}\n\nVerified Evidence:\n{evidence_text}"

    try:
        completion = client.chat.completions.create(
            model=config.FEATHERLESS_MODEL,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        raw_text = completion.choices[0].message.content or ""
        sanitized_text, valid_cites, stripped = validate_citations_and_claims(raw_text, evidence_map)

        return ExplainResponse(
            explanation=sanitized_text,
            valid_citations=valid_cites,
            invalid_citations_stripped=stripped,
            grounded=len(stripped) == 0,
            model_used=config.FEATHERLESS_MODEL,
            error=None,
        )

    except Exception as e:
        return ExplainResponse(
            explanation=f"AI explanation unavailable: {str(e)[:150]}. "
                        "Please inspect the verified source evidence directly.",
            valid_citations=[],
            invalid_citations_stripped=[],
            grounded=True,
            error=str(e),
        )
