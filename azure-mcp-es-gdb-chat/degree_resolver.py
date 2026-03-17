# degree_resolver.py
from typing import List, Tuple
import difflib
import re

# Basic normalization
def _norm(s: str) -> str:
    if s is None:
        return ""
    s = s.strip().lower()
    # collapse punctuation, extra whitespace
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def _token_set(s: str):
    return set([t for t in _norm(s).split() if t])

def score_similarity(a: str, b: str) -> float:
    """
    Combined score:
      - difflib.SequenceMatcher ratio
      - token overlap (Jaccard-like)
    Weighted combination to prefer high lexical similarity and token overlap.
    """
    if not a or not b:
        return 0.0
    na = _norm(a)
    nb = _norm(b)
    seq = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = _token_set(a), _token_set(b)
    if not ta or not tb:
        token_score = 0.0
    else:
        inter = ta.intersection(tb)
        union = ta.union(tb)
        token_score = len(inter) / len(union)
    # weight them: token_score more important for multi-word degrees
    return 0.55 * token_score + 0.45 * seq

def find_similar_degrees(query_text: str, top_degrees: List[str], top_n: int = 8, min_score: float = 0.38) -> List[Tuple[str, float]]:
    """
    Return list of (degree_string, score) sorted by score desc.
    - query_text: portion likely referring to degree (e.g., "MBA", "master business", "business administration")
    - top_degrees: canonical list of degrees from DB (e.g., the top 500)
    - min_score: filter threshold to avoid weak matches; tune as needed
    """
    q = _norm(query_text)
    if not q:
        return []

    # Some common abbreviation expansions to boost matching
    abbrev_map = {
        "mba": "master of business administration",
        "ms": "master of science",
        "msc": "master of science",
        "bs": "bachelor of science",
        "ba": "bachelor of arts",
        "mbe": "master of business economics",
        "phd": "doctor of philosophy",
        "bsc": "bachelor of science"
    }

    candidates = []
    q_variants = {q}
    # add abbreviation expansion if exact
    qtokens = q.split()
    if len(qtokens) == 1 and qtokens[0] in abbrev_map:
        q_variants.add(_norm(abbrev_map[qtokens[0]]))

    # add some small permutations: drop dots, replace '&' with and
    q_variants.add(q.replace("&", "and"))
    q_variants.add(q.replace("-", " "))
    q_variants.add(re.sub(r"\b(degree|major|studied|in)\b", "", q).strip())

    # Score every candidate, keep top_n above threshold
    for deg in top_degrees:
        if not deg:
            continue
        best = 0.0
        for v in q_variants:
            s = score_similarity(v, deg)
            if s > best:
                best = s
        if best >= min_score:
            candidates.append((deg, best))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:top_n]