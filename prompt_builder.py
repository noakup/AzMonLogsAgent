"""Prompt Builder for AKS / Container Log Analytics

Implements the layered prompt strategy described in containers_capsule/prompt_guidelines.md (relocated from docs/containers_capsule/).

Layers:
  L0 System Core                -> prompts/system_base.txt (fallback inline default)
  L1 Domain Capsule             -> prompts/domain_capsule_containerlogs.txt (optional)
    L2 Function Index (names)     -> parsed from containers_capsule/kql_functions_containerlogs.kql (new location)
  L3 Dynamic Retrieval Addendum -> lightweight keyword heuristic snippets
  L4 Clarified User Query       -> minimal normalization
  L5 Output Directive           -> decides explanation vs KQL-only
  L6 Assembly / Version Tag     -> final formatted string

Usage:
  from prompt_builder import build_prompt
  full_prompt, meta = build_prompt("why so many errors in payments service last 2h?", {})

The function returns (prompt_text, metadata_dict) so callers can log metadata (hashes, version, token estimates).

NOTE: This is intentionally dependency-light and avoids external NLP libs; you can plug in a richer intent classifier later.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import textwrap
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from typing import Dict, List, Optional, Tuple

PROMPT_SCHEMA_VERSION = 2
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# ------------------------- File Loading Helpers ------------------------- #

def _safe_read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def _fallback_system_prompt() -> str:
    return textwrap.dedent(
        f"""# PromptSchemaVersion:{PROMPT_SCHEMA_VERSION}\nROLE: AKS Container Observability Assistant\nRules:\n- Default timeframe: last 1h if unspecified.\n- Do not fabricate table / column names.\n- Use ContainerLogV2 for container app logs.\n- Error = LogLevel in (CRITICAL, ERROR) OR LogSource=='stderr'.\n- Provide counts + rates for error comparisons.\n- Mask potential secrets (Bearer tokens, keys, PEM blocks).\n- KQL only unless user explicitly asks for explanation / why / describe.\n"""
    ).strip()


# ------------------------- Function Index Extraction ------------------------- #
FUNC_PATTERN = re.compile(r"^let\s+([A-Za-z0-9_]+)\s*=\s*\(")
# We'll implement more resilient extraction without brittle regex.

def extract_function_index(kql_text: str) -> List[str]:
    """Extract top-level 'let Name = (params){' patterns from the KQL helper file.
    We only keep the signature (name + parameter list) to minimize token usage.
    """
    lines = kql_text.splitlines()
    signatures: List[str] = []
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith("let ") and "={" not in line_stripped:
            # Pattern: let FunctionName = (params){
            match = re.match(r"let\s+([A-Za-z0-9_]+)\s*=\s*\(([^)]*)\)\{", line_stripped)
            if match:
                name, params = match.groups()
                signatures.append(f"{name}({params.strip()})")
    return signatures


# ------------------------- Keyword Heuristics --------------------------- #
KEYWORD_CONTEXT_MAP = {
    "error": "Errors classified via LogLevel CRITICAL/ERROR or stderr stream.",
    "latency": "Latency extracted with regex latency[=:]([0-9]+)ms into LatencyMs.",
    "slow": "Latency extracted with regex latency[=:]([0-9]+)ms into LatencyMs.",
    "crash": "Crash loops require join with KubePodInventory restart counts.",
    "restart": "Crash loops require join with KubePodInventory restart counts.",
    "stack": "Stack traces detected if message contains Exception, Traceback, or ' at '.",
    "trace": "Stack traces detected if message contains Exception, Traceback, or ' at '.",
    "status": "If LogMessage dynamic has field 'status', filter with tostring(LogMessage.status).",
    "500": "Structured status filter example: where tostring(LogMessage.status)=='500'",
    "noisy": "Noisy container detection = count lines per container or workload.",
    "volume": "High volume logs -> aggregate by WorkloadName then count().",
}


def derive_context_addendum(user_query: str) -> str:
    q_lower = user_query.lower()
    hits = []
    for kw, snippet in KEYWORD_CONTEXT_MAP.items():
        if kw in q_lower:
            hits.append(snippet)
    hits = list(dict.fromkeys(hits))  # de-duplicate preserving order
    if not hits:
        return ""
    return "\n".join(f"- {h}" for h in hits)


# ------------------------- Clarification & Output Mode ------------------ #

def clarify_query(user_query: str) -> str:
    """Light normalization: trim, collapse whitespace. (Avoid semantic rewrite here)."""
    normalized = re.sub(r"\s+", " ", user_query.strip())
    return normalized


def decide_output_mode(clarified_query: str) -> Tuple[str, str]:
    """Return (mode, directive_text)."""
    ql = clarified_query.lower()
    needs_explanation = any(w in ql for w in ["why", "explain", "describe", "root cause", "reason"])  # simple heuristic
    if needs_explanation:
        return (
            "explanation+sql",
            "Output Mode: Provide a concise explanation paragraph first, then a KQL block."
        )
    return ("kql-only", "Output Mode: Return only the KQL query (no prose).")


# ------------------------- Secret Mask (future hook) -------------------- #
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS-style as generic example
    re.compile(r"Bearer\s+[A-Za-z0-9-_\.]+"),
    re.compile(r"-----BEGIN [A-Z ]+-----"),
]


def mask_secrets(text: str) -> str:
    masked = text
    for pat in SECRET_PATTERNS:
        masked = pat.sub("[REDACTED]", masked)
    return masked


# ------------------------- Hash Utility --------------------------------- #

def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ------------------------- Assembly Dataclasses ------------------------- #
@dataclass
class PromptMetadata:
    schema_version: int
    system_hash: str
    capsule_included: bool
    function_index_hash: str
    retrieval_keywords: List[str]
    output_mode: str
    timestamp_utc: str


# ------------------------- Main Builder -------------------------------- #

def build_prompt(
    user_query: str,
    intent_meta: Optional[Dict] = None,
    *,
    include_capsule: bool = True,
    force_kql_only: bool = False,
) -> Tuple[str, Dict]:
    intent_meta = intent_meta or {}

    # L0 System
    # Prefer relocated container capsule system base, fallback to legacy prompts path (back-compat)
    system_path_new = os.path.join(REPO_ROOT, "containers_capsule", "system_base.txt")
    system_path_legacy = os.path.join(REPO_ROOT, "prompts", "system_base.txt")
    if os.path.exists(system_path_new):
        system_text = _safe_read(system_path_new)
    else:
        system_text = _safe_read(system_path_legacy)
    if not system_text:
        system_text = _fallback_system_prompt()

    # L1 Capsule
    capsule_path_new = os.path.join(REPO_ROOT, "containers_capsule", "domain_capsule_containerlogs.txt")
    capsule_path_legacy = os.path.join(REPO_ROOT, "prompts", "domain_capsule_containerlogs.txt")
    if os.path.exists(capsule_path_new):
        capsule_text = _safe_read(capsule_path_new)
    else:
        capsule_text = _safe_read(capsule_path_legacy)
    capsule_included = bool(capsule_text and include_capsule)

    # L2 Function Index: new top-level capsule path first, fallback to legacy docs path for backward compatibility
    functions_kql_path_new = os.path.join(REPO_ROOT, "containers_capsule", "kql_functions_containerlogs.kql")
    functions_kql_path_legacy = os.path.join(REPO_ROOT, "docs", "containers_capsule", "kql_functions_containerlogs.kql")
    functions_kql_path_fallback_old = os.path.join(REPO_ROOT, "docs", "kql_functions_containerlogs.kql")  # very old layout
    if os.path.exists(functions_kql_path_new):
        functions_kql_path = functions_kql_path_new
    elif os.path.exists(functions_kql_path_legacy):
        functions_kql_path = functions_kql_path_legacy
    else:
        functions_kql_path = functions_kql_path_fallback_old
    function_raw = _safe_read(functions_kql_path)
    fn_index = extract_function_index(function_raw)
    fn_index_block = "\n".join(f"- {f}" for f in fn_index) if fn_index else ""

    # L3 Retrieval
    addendum = derive_context_addendum(user_query)
    retrieval_keywords = [k for k in KEYWORD_CONTEXT_MAP.keys() if k in user_query.lower()]

    # L4 Clarified Query
    clarified = clarify_query(user_query)

    # L5 Output Mode
    output_mode, directive = decide_output_mode(clarified)
    if force_kql_only and output_mode != "kql-only":
        # Override to strict KQL only mode for translation pipeline usage
        output_mode = "kql-only"
        directive = "Output Mode: Return only the KQL query (no prose)."

    # Assemble
    parts: List[str] = [system_text]
    if capsule_included:
        parts.append("Domain Capsule:\n" + capsule_text)
    if fn_index_block:
        parts.append("Functions:\n" + fn_index_block)
    if addendum:
        parts.append("Context Addendum:\n" + addendum)
    parts.append("User Query (clarified):\n" + clarified)
    parts.append(directive)

    full_prompt = "\n\n".join(p for p in parts if p.strip())
    full_prompt = mask_secrets(full_prompt)

    meta = PromptMetadata(
        schema_version=PROMPT_SCHEMA_VERSION,
        system_hash=stable_hash(system_text),
        capsule_included=capsule_included,
        function_index_hash=stable_hash(fn_index_block),
        retrieval_keywords=retrieval_keywords,
        output_mode=output_mode,
        timestamp_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    return full_prompt, asdict(meta)


# ------------------------- Demo / CLI ----------------------------------- #
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build an AKS Container Logs prompt")
    parser.add_argument("query", help="User natural language query")
    parser.add_argument("--no-capsule", action="store_true", help="Exclude domain capsule layer")
    args = parser.parse_args()

    prompt, metadata = build_prompt(args.query, include_capsule=not args.no_capsule)
    print("=== PROMPT BEGIN ===")
    print(prompt)
    print("=== PROMPT END ===\n")
    print("Metadata:\n" + json.dumps(metadata, indent=2))
