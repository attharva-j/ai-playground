# prop_resolver.py
import re
import difflib
import threading
import time
from typing import Dict, Set, Tuple, Optional, Callable, Any

# --- lightweight normalization & aliasing ---

def _norm(s: str) -> str:
    if not s: return ""
    s = s.strip()
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)  # split camel/PascalCase
    s = s.replace("-", " ").replace("_", " ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.casefold().strip()

ALIASES = {
    "full name": "FullName",
    "job title": "CurrentTitle",
    "company name": "CompanyName",
    "current company": "CurrentCompanyName",
    "sector": "industry",
    "industry sector": "industry",
}

def _alias(s: str) -> str:
    key = _norm(s)
    return ALIASES.get(key, s)

# --- schema cache ---

class SchemaCache:
    def __init__(self, gdb_query_fn: Callable[..., Any], ttl_seconds: int = 3600):
        self._q = gdb_query_fn
        self._ttl = ttl_seconds
        self._ts = 0.0
        self._lock = threading.Lock()
        self._label_props: Dict[str, Set[str]] = {}

    def _load(self, database: Optional[str] = None):
        rows = self._q(
            cypher=("CALL db.schema.nodeTypeProperties() "
                    "YIELD nodeLabels, propertyName "
                    "RETURN nodeLabels, propertyName"),
            database=database,
        )
        lp: Dict[str, Set[str]] = {}
        for r in rows or []:
            labels = r.get("nodeLabels") or []
            prop = r.get("propertyName")
            if not prop: 
                continue
            for lbl in labels:
                lp.setdefault(lbl, set()).add(prop)
        with self._lock:
            self._label_props = lp
            self._ts = time.time()

    def get(self, database: Optional[str] = None) -> Dict[str, Set[str]]:
        with self._lock:
            stale = not self._label_props or (time.time() - self._ts) > self._ttl
        if stale:
            self._load(database)
        with self._lock:
            return self._label_props

class PropertyResolver:
    def __init__(self, gdb_query_fn: Callable[..., Any], ttl_seconds=3600, min_cutoff=0.78):
        self._schema = SchemaCache(gdb_query_fn, ttl_seconds)
        self._cutoff = min_cutoff

    def infer_var_labels(self, cypher: str) -> Dict[str, Set[str]]:
        var2labels: Dict[str, Set[str]] = {}
        for m in re.finditer(r"\(([A-Za-z_]\w*)\s*:\s*([A-Za-z_][A-Za-z0-9_:]*)\)", cypher):
            var = m.group(1)
            lbls = [x for x in m.group(2).split(":") if x]
            var2labels.setdefault(var, set()).update(lbls)
        return var2labels

    def best_property(self, props: Set[str], token: str) -> Tuple[Optional[str], float]:
        if not token or not props:
            return (None, 0.0)

        # exact
        if token in props:
            return (token, 1.0)

        # alias -> exact
        aliased = _alias(token)
        if aliased in props:
            return (aliased, 0.98)

        # normalized matching
        norm_token = _norm(aliased)
        norm_map = {p: _norm(p) for p in props}

        for p, sig in norm_map.items():
            if sig == norm_token:
                return (p, 0.95)

        # fuzzy normalized
        choices = list(norm_map.values())
        best = difflib.get_close_matches(norm_token, choices, n=1, cutoff=self._cutoff)
        if best:
            sig = best[0]
            candidates = [p for p, s in norm_map.items() if s == sig]
            candidates.sort(key=len)
            from difflib import SequenceMatcher
            return (candidates[0], SequenceMatcher(None, norm_token, sig).ratio())

        return (None, 0.0)

    def resolve_token(self, var: str, token: str, var2labels: Dict[str, Set[str]], label_props: Dict[str, Set[str]]) -> Tuple[str, float]:
        labels = var2labels.get(var) or set()
        props: Set[str] = set()
        for lbl in labels:
            props |= set(label_props.get(lbl, set()))
        if not props:
            # fallback: all props (last resort)
            for s in label_props.values():
                props |= s
        best, conf = self.best_property(props, token)
        return (best or token, conf)