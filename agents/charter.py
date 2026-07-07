"""Charter grounding — give each agent only the charter sections its job needs.

Hermes-style: agents have small, single-responsibility prompts. We do NOT copy the
whole charter into every agent (token waste + dilutes focus). Instead the charter
(CHARTER.md, per-instance) is addressable by section, and each AgentSpec declares the section
KEYS it needs (registry.py). Grounding is assembled from the single source at call
time — curated, bounded, and never drifting from the charter.

If an agent's composed system prompt exceeds the budget, that's the signal to either
trim its grounding or SPLIT the agent (it's doing too much) — see base.SYSTEM_PROMPT_TOKEN_BUDGET.
"""
from __future__ import annotations

import os

DEFAULT_PATH = os.getenv("EVOLVE_CHARTER_PATH", "CHARTER.md")

# grounding key -> a distinctive substring of the section's `## ` header (lowercased)
_KEYS = {
    "thesis": "thesis",
    "is": "*is*",
    "project-kind": "project kind",          # what kind of project this is + its primary interface(s) + build/run/test
    "surfaces": "cross-surface",
    "non-goals": "non-goals",
    "scope": "scope",
    "autonomy": "autonomy",
    "principles": "engineering principles",   # non-functional constraints (preconfigure, minimize calls...)
    "contracts": "external contract",         # consumers outside this repo (companion clients / shared APIs)
    "stack": "stack",                         # languages/frameworks + repo layout the agents must respect
    "test-state": "test-target state",        # optional: what blank/seeded mean for THIS product + which item classes need which
}


def parse(path: str = DEFAULT_PATH) -> dict[str, str]:
    """{header_line: section_text_including_header} for each level-2 (`## `) section."""
    if not os.path.exists(path):
        return {}
    sections: dict[str, str] = {}
    cur, buf = None, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("## "):
                if cur is not None:
                    sections[cur] = "".join(buf).rstrip()
                cur, buf = line.strip(), [line]
            elif cur is not None:
                buf.append(line)
    if cur is not None:
        sections[cur] = "".join(buf).rstrip()
    return sections


def keyed(path: str = DEFAULT_PATH) -> dict[str, str]:
    """Map each grounding key to its section text (only keys whose section is found)."""
    secs = parse(path)
    out: dict[str, str] = {}
    for key, sub in _KEYS.items():
        for header, body in secs.items():
            if sub in header.lower():
                out[key] = body
                break
    return out


def grounding(keys: list[str], path: str = DEFAULT_PATH) -> str:
    """Assemble the curated charter excerpts for the given keys (in charter order)."""
    if not keys:
        return ""
    k = keyed(path)
    ordered = [key for key in _KEYS if key in keys]      # stable charter order
    chosen = [k[key] for key in ordered if key in k]
    if not chosen:
        return ""
    product = os.getenv("EVOLVE_PRODUCT_NAME", "Project")
    return (f"# {product} charter — excerpts relevant to your job (the vision authority; "
            "judge against these, do not invent)\n\n" + "\n\n".join(chosen))


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) — no tokenizer dependency."""
    return (len(text) + 3) // 4
