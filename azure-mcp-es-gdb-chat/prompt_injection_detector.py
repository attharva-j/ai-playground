"""
prompt_injection_detector.py

Simple heuristic-based detector for prompt-injection attempts.

Contains:
- is_prompt_injection(query: str) -> bool
- explain_prompt_injection(query: str) -> list[str]  # returns matched rule descriptions

Notes:
- This is a heuristic detector (regex / phrase matches). It is NOT perfect.
- Consider improving with ML-based classifiers or allowlist/denylist tuning for production.
"""

import re
from typing import List

# Precompile regex patterns for performance
# Each tuple is (compiled_regex, description)
_PATTERNS = [
    # Direct override / ignore prior instructions
    (re.compile(r"\bignore (all )?(previous|above|prior) (instructions|prompts|messages)\b", re.I),
     "Instruction to ignore previous instructions"),
    (re.compile(r"\bdisregard (all )?(previous|above|prior) (instructions|prompts|messages)\b", re.I),
     "Instruction to disregard prior context"),
    (re.compile(r"\bforget (the )?(previous|above|prior) (instructions|prompts|messages)\b", re.I),
     "Instruction to forget previous context"),

    # Jailbreak / developer mode / bypass content policy
    (re.compile(r"\b(dev(eloper)? mode|developer-mode|enable developer mode|jailbreak|jail broken|jail[- ]?break|unblock me|bypass (the )?(filters|policy|rules))\b", re.I),
     "Attempt to enable developer/jailbreak/bypass mode"),
    (re.compile(r"\bignore (all )?(safety|policy|content) (rules|guidelines|checks)\b", re.I),
     "Request to ignore safety or policy rules"),
    (re.compile(r"\bdisable (safety|content|filter|moderation)\b", re.I),
     "Request to disable safety/filtering"),

    # Role impersonation/system role injection
    (re.compile(r"\byou are (now|from now on|acting as|to be|the) (a |an )?([a-z0-9_ -]{2,50})\b", re.I),
     "Role assignment (you are / act as)"),
    (re.compile(r"\b(system|assistant|user|admin|operator)\s*:\s*", re.I),
     "Explicit system/role message token"),

    # Special tokens / separators often used in prompt injection
    (re.compile(r"(^|\n)[#\-=]{3,}\s*(system|instruction|prompt)?", re.I),
     "Prompt-style separators or system/instruction blocks"),

    # Requests to reveal hidden/secret/internal data
    (re.compile(r"\b(api key|secret key|password|credentials|ssn|social security|token|private key|secret)\b", re.I),
     "Request for secrets or sensitive data"),
    (re.compile(r"\b(send|exfiltrate|leak|reveal|return) (all )?(files|secrets|data|attachments|messages)\b", re.I),
     "Request to exfiltrate files or secrets"),

    # Execution / file system / external actions
    (re.compile(r"\b(run|execute|open|download|install|click|launch|shell|bash|sudo|rm -rf)\b", re.I),
     "Request to execute commands or access system"),
    (re.compile(r"\b(go to|visit|browse|scrape) (https?://)?[^\s]+\b", re.I),
     "Request to browse or fetch external URLs"),

    # Strongly-phrased absolute-only output constraints (used in some jailbreaks)
    (re.compile(r"\b(only respond with|respond only with|answer only with|output only)\b", re.I),
     "Demand for 'only' specific output that may attempt to constrain model"),

    # "Act as" personas commonly used in jailbreaks (DAN, Developer, etc.)
    (re.compile(r"\b(act as|play the role of|become|you are now|from now on) (DAN|Developer|Developer Mode|Master|SysOp|root)\b", re.I),
     "Persona-based jailbreak attempt"),

    # Requests to ignore assistant's policies explicitly
    (re.compile(r"\b(do not follow|do not obey|disobey) (the )?(rules|policy|instructions)\b", re.I),
     "Explicit request to disobey rules/policy"),
]

def explain_prompt_injection(query: str) -> List[str]:
    """
    Return a list of descriptions for any matched prompt-injection heuristics.
    """
    matches = []
    for regex, desc in _PATTERNS:
        if regex.search(query):
            matches.append(desc)
    return matches

def is_prompt_injection(query: str) -> bool:
    """
    Heuristic detector that returns True if the query likely contains a prompt-injection attempt.
    """
    if not isinstance(query, str):
        return False

    q = query.strip()

    if not q:
        return False

    if explain_prompt_injection(q):
        return True

    # Additional heuristic: presence of embedded system-like message blocks inside triple backticks or quotes
    if re.search(r"(```|\"\"\"|---)[\s\S]{0,1000}?(system|assistant|ignore|jailbreak|developer)[\s\S]{0,1000}?(```|\"\"\"|---)", q, re.I):
        return True

    # Heuristic: extremely long prompt that includes 'system' and 'instructions' keywords
    if len(q) > 200 and re.search(r"\bsystem\b", q, re.I) and re.search(r"\binstruction(s)?\b", q, re.I):
        return True

    return False

__all__ = ["is_prompt_injection", "explain_prompt_injection"]
