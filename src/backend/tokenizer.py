"""Code-aware tokenizer for NextGen Code Explorer.

Splits camelCase, PascalCase, snake_case, kebab-case, dots, slashes, and digits.
Supports token preservation, query stopword filtering, and light suffix stemming.
"""

from __future__ import annotations

import re
from typing import List, Set


# Common English and query conversational stopwords
QUERY_STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "if", "in", "into", "is", "isn't",
    "it", "it's", "its", "itself", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the",
    "their", "theirs", "them", "themselves", "then", "there", "there's", "these",
    "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "were", "weren't", "what", "what's", "when",
    "where", "where's", "which", "while", "who", "whom", "why", "with", "won't",
    "would", "wouldn't", "you", "your", "yours", "yourself", "yourselves",
    # Query intent filler words
    "code", "show", "find", "located", "handled", "implemented", "defined", "place",
}


def split_identifier(identifier: str) -> List[str]:
    """Split camelCase, PascalCase, snake_case, and kebab-case into components.

    Example:
        'saveUploadedFile' -> ['save', 'uploaded', 'file']
        'getHTTPResponseCode' -> ['get', 'http', 'response', 'code']
        'user_auth_v2' -> ['user', 'auth', 'v2', 'v', '2']
    """
    if not identifier:
        return []

    # Replace common delimiters with space
    cleaned = re.sub(r"[_\-./\\:]+", " ", identifier)
    parts = cleaned.split()

    results: List[str] = []

    # Also capture original joined identifier without punctuation
    flat = re.sub(r"[^a-zA-Z0-9]", "", identifier).lower()
    if flat and len(flat) > 1:
        results.append(flat)

    # Preserve alphanumeric sub-words (e.g. 'v2')
    for p in parts:
        p_lower = p.lower()
        if p_lower and p_lower not in results:
            results.append(p_lower)

    # Insert spaces between camelCase / PascalCase / Acronym boundaries
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", cleaned)
    s2 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s1)
    s3 = re.sub(r"([a-zA-Z])([0-9])", r"\1 \2", s2)
    s4 = re.sub(r"([0-9])([a-zA-Z])", r"\1 \2", s3)

    raw_tokens = [t.lower() for t in s4.split() if t.strip()]

    for token in raw_tokens:
        if token and token not in results:
            results.append(token)

    return results


def stem_token(word: str) -> str:
    """Apply light, deterministic suffix stemming for code and English terms.

    Handles plurals (-s, -es, -ies), past tense (-ed), continuous (-ing), etc.
    """
    w = word.lower()
    if len(w) <= 3:
        return w

    # -ies -> -y (e.g. repositories -> repositor -> repositori / repo)
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"

    # -sses -> -ss
    if w.endswith("sses"):
        return w[:-2]

    # -es (e.g., classes -> class, boxes -> box, searches -> search)
    if w.endswith("es") and len(w) > 4:
        if w.endswith(("shes", "ches", "xes", "zes", "sses")):
            return w[:-2]
        return w[:-1]

    # -s (e.g., tokens -> token, files -> file), but don't strip from 'ss' or 'us' or 'is'
    if w.endswith("s") and not w.endswith(("ss", "us", "is")) and len(w) > 3:
        return w[:-1]

    # -ing (e.g., parsing -> pars, filtering -> filter)
    if w.endswith("ing") and len(w) > 5:
        base = w[:-3]
        if base.endswith(("bb", "dd", "gg", "mm", "nn", "pp", "rr", "tt")):
            base = base[:-1]
        return base

    # -ed (e.g., extracted -> extract, scanned -> scan)
    if w.endswith("ed") and len(w) > 4:
        base = w[:-2]
        if base.endswith(("bb", "dd", "gg", "mm", "nn", "pp", "rr", "tt")):
            base = base[:-1]
        return base

    return w


def tokenize(
    text: str,
    remove_stopwords: bool = False,
    apply_stemming: bool = True,
    preserve_raw: bool = True,
) -> List[str]:
    """Tokenize a block of code or query text.

    Args:
        text: Source text to tokenize.
        remove_stopwords: Whether to drop English/query stopwords.
        apply_stemming: Whether to apply suffix stemming.
        preserve_raw: Whether to include unstemmed tokens alongside stemmed tokens.

    Returns:
        List of normalized string tokens in document order.
    """
    if not text:
        return []

    # Extract words/identifier-like tokens
    raw_words = re.findall(r"[a-zA-Z0-9_\-./]+", text)
    tokens: List[str] = []

    for word in raw_words:
        sub_tokens = split_identifier(word)
        for sub in sub_tokens:
            if len(sub) < 1:
                continue
            if remove_stopwords and sub in QUERY_STOPWORDS:
                continue

            stemmed = stem_token(sub) if apply_stemming else sub

            if preserve_raw and stemmed != sub:
                tokens.append(sub)
            tokens.append(stemmed)

    return tokens
