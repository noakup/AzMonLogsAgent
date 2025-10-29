#!/usr/bin/env python3
"""
Enhanced Natural Language to KQL Translation
This version actually uses the example files to provide context to the AI
"""

import os
import json
import re
from typing import List, Optional, Dict, Tuple
from datetime import datetime

from prompt_builder import build_prompt, stable_hash  # type: ignore

from azure_openai_utils import (
    run_chat,
    emit_chat_event,
)

# ---------------- Token & Embedding Utilities ---------------- #
def _count_tokens(text: str) -> int:
    """Best-effort token count.
    Prefers tiktoken; falls back to simple word segmentation.
    """
    try:
        import tiktoken  # type: ignore
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Approximate: count word-like segments
        return len(re.findall(r"\w+", text))

def _maybe_embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    """Return list of embedding vectors or None if unavailable.

    Always attempts to obtain embeddings (no user toggle). Falls back silently if
    OpenAI credentials or model are not available. Keeps behavior non-fatal for
    offline / test environments.
    """
    model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    try:
        # OpenAI python SDK v1.x style
        from openai import OpenAI  # type: ignore
        client = OpenAI()
        resp = client.embeddings.create(model=model_name, input=texts)
        vectors: List[List[float]] = []
        for item in resp.data:
            vec = item.embedding
            # L2 normalize
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            vectors.append([v / norm for v in vec])
        return vectors
    except Exception as exc:
        print(f"[embeddings] disabled (error: {exc})")
        return None

def _cosine(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))

# Backward compatibility alias expected by some legacy tests
def chat_completion(*args, **kwargs):  # type: ignore
    """Compatibility shim.

    Supports two invocation styles:
      1. chat_completion(cfg_dict, payload_dict)  # legacy tests monkeypatch this
      2. chat_completion(system_prompt=..., user_prompt=..., purpose=..., ...)
    """
    if len(args) == 2 and isinstance(args[0], dict) and isinstance(args[1], dict):
        cfg, payload = args
        return run_chat(
            system_prompt=payload.get("system", ""),
            user_prompt=payload.get("user", ""),
            purpose=cfg.get("purpose", "translate"),
            allow_escalation=cfg.get("allow_escalation", True),
            debug_prefix=cfg.get("debug_prefix", "Translate"),
        )
    return run_chat(*args, **kwargs)

def load_domain_context(domain: str, nl_question: Optional[str] = None) -> Dict[str, str]:
    """Unified domain context loader.

    Returns standardized keys:
      fewshots: joined examples (selected or raw fallback)
      selected_example_count: number of relevance-selected examples
      function_signatures / function_count
      capsule: domain capsule excerpt (if available)
      selected_examples_present: 'True'|'False'

    For containers: delegates to load_container_examples (existing behavior).
    For appinsights: aggregates multiple example files, parses markdown questions, applies relevance selection.
    """
    if domain == "containers":
        return load_container_examples(nl_question)

    # Application Insights domain
    example_files = [
        "app_insights_capsule/kql_examples/app_requests_kql_examples.md",
        "app_insights_capsule/kql_examples/app_exceptions_kql_examples.md",
        "app_insights_capsule/kql_examples/app_traces_kql_examples.md",
        "app_insights_capsule/kql_examples/app_performance_kql_examples.md",
    ]
    parsed_examples: List[Dict[str, str]] = []
    for path in example_files:
        if os.path.exists(path):
            parsed_examples.extend(_parse_container_fewshots(path))  # Reuse same parser (bold+fence format)
    selected: List[Dict[str, str]] = []
    if nl_question and parsed_examples:
        selected = _select_relevant_fewshots(nl_question, parsed_examples, top_k=3)
    if selected:
        blocks = [f"Q: {ex['question']}\nKQL:\n{ex['kql']}" for ex in selected]
        fewshots_block = "\n\n".join(blocks)
    else:
        # Fallback: include truncated concatenation of raw files
        raw_concat = []
        for path in example_files:
            if os.path.exists(path):
                raw_concat.append(_read_file(path, limit=900))
        fewshots_block = "\n\n".join(raw_concat)[:1600]

    # Capsule for app insights (optional) - attempt read
    capsule_path = "app_insights_capsule/README.md"
    capsule_excerpt = _read_file(capsule_path, limit=600) if os.path.exists(capsule_path) else "(No capsule)"
    # No dedicated function signatures currently for app insights domain
    return {
        "fewshots": fewshots_block,
        "capsule": capsule_excerpt,
        "function_signatures": "(No function signatures)",
        "function_count": "0",
        "selected_example_count": str(len(selected)),
        "selected_examples_present": str(bool(selected))
    }

# ------------------ Container Domain Support ------------------ #
CONTAINER_KEYWORDS = [
    # Original + singular
    "container", "containerlogv2", "pod", "namespace", "kube", "crashloop", "crashloopbackoff", "stderr", "latency", "stack trace", "image",
    "workload", "latencyms", "containerlog", "kubernetes", "k8s", "daemonset", "statefulset", "deployment",
    # Plural / additional variants
    "pods", "namespaces", "containers", "restart", "restarts", "pending", "schedule", "scheduling"
]

# Application Insights domain keywords (explicitly provided by user)
APPINSIGHTS_KEYWORDS = [
    "application", "applications", "app", "apps", "trace", "traces", "apptraces",
    "request", "requests", "apprequests", "dependency", "dependencies", "appdependencies",
    "exception", "exceptions", "appexceptions", "customevent", "customevents"
]

# Regex pattern to catch common container / k8s table names or metrics even if keywords above are absent
import re as _re
_CONTAINER_TABLE_REGEX = _re.compile(r"\b(containerlogv2|containerlog|kubepodinventory|kube[pP]od|insightsmetrics|containerinventory|kubeevents?)\b", _re.IGNORECASE)
_APP_TABLE_REGEX = _re.compile(r"\b(apprequests|appexceptions|apptraces|appdependencies|apppageviews|appcustomevents)\b", _re.IGNORECASE)

def detect_domain(nl_question: str) -> str:
    """Heuristic domain detection with explicit Application Insights keyword set.

    Logic:
      1. Collect matched container keywords & app insights keywords.
      2. Add table regex matches to respective sets.
      3. Container special heuristic: if ("pod" or "pods") AND "pending" present -> force containers.
      4. Resolution:
         - If only one side has matches -> choose that domain.
         - If both have matches -> prefer containers if container table names present, else prefer appinsights.
         - If neither side matched -> raise ValueError to notify caller (no silent default).
    """
    q = nl_question.lower()
    matched_container = {kw for kw in CONTAINER_KEYWORDS if kw in q}
    matched_app = {kw for kw in APPINSIGHTS_KEYWORDS if kw in q}

    # Table regex matches
    if _CONTAINER_TABLE_REGEX.search(q):
        matched_container.add("<table-match>")
    if _APP_TABLE_REGEX.search(q):
        matched_app.add("<table-match>")

    # Container special heuristic: pods pending scenario
    if ("pod" in q or "pods" in q) and "pending" in q:
        matched_container.add("<pods-pending>")

    # Log diagnostic info
    print(f"[domain-detect] q='{nl_question}' container_matches={sorted(matched_container)} app_matches={sorted(matched_app)}")

    if matched_container and not matched_app:
        print("[domain-detect] chosen=containers (exclusive container matches)")
        return "containers"
    if matched_app and not matched_container:
        print("[domain-detect] chosen=appinsights (exclusive app matches)")
        return "appinsights"
    if matched_container and matched_app:
        # Prefer containers if a container table or pods-pending signal present
        if any(sig in matched_container for sig in ("<table-match>", "<pods-pending>")):
            print("[domain-detect] chosen=containers (conflict; container strong signal)")
            return "containers"
        print("[domain-detect] chosen=appinsights (conflict; default to appinsights)")
        return "appinsights"

    # No matches; raise explicit exception
    raise ValueError("Unable to classify domain. Please include explicit domain indicators (e.g. 'pod', 'containerlogv2' or 'request', 'apprequests').")

def _read_file(path: str, limit: int = 1600) -> str:
    if not os.path.exists(path):
        return "File not found"
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    if len(data) > limit:
        return data[:limit] + "..."
    return data

def parse_container_function_signatures(kql_text: str) -> List[str]:
    """Backward-compatible thin wrapper returning only signature strings.
    Internally uses the richer parser with descriptions.
    """
    return [s for s, _ in parse_container_function_signatures_with_docs(kql_text)]

def parse_container_function_signatures_with_docs(kql_text: str) -> List[Tuple[str, str]]:
    """Parse function signatures with brief description (taken from preceding // comment).

    Supports multi-line declarations of the form:
        let FuncName =\n    (Param1:type, Param2:type)\n    {
    or single-line: let FuncName = (Param1:type){

    Returns list of tuples: ("FuncName(paramlist)", "Description or empty").
    """
    lines = kql_text.splitlines()
    results: List[Tuple[str, str]] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if stripped.startswith("let "):
            # Capture preceding comment block (contiguous // lines above)
            desc = ""
            j = i - 1
            comment_lines: List[str] = []
            while j >= 0:
                prev = lines[j].strip()
                if prev.startswith("//"):
                    # prepend (to preserve order after loop)
                    comment_lines.insert(0, prev.lstrip("/ "))
                    j -= 1
                    continue
                break
            if comment_lines:
                # Use the last non-empty comment line as summary (shortened)
                for c in reversed(comment_lines):
                    if c.strip():
                        desc = c.strip()
                        break
                if len(desc) > 110:
                    desc = desc[:107] + "..."

            # Accumulate declaration until we see '{' or hit 6 lines
            decl_lines = [stripped]
            k = i + 1
            found_brace = '{' in stripped
            while not found_brace and k < len(lines) and k <= i + 5:
                nxt = lines[k].strip()
                decl_lines.append(nxt)
                if '{' in nxt:
                    found_brace = True
                k += 1
            decl = " ".join(decl_lines)
            # Collapse extra spaces
            decl = re.sub(r"\s+", " ", decl)
            m = re.match(r"let\s+([A-Za-z0-9_]+)\s*=\s*\((.*?)\)\s*\{", decl)
            if m:
                name, params = m.groups()
                signature = f"{name}({params.strip()})"
                results.append((signature, desc))
            i = k
            continue
        i += 1
    return results

def _parse_container_fewshots(path: str) -> List[Dict[str, str]]:
    """Parse few-shot examples into structured list of {question, kql}.

    Supported formats:
      1. Legacy plain format:
         Q: some question\nKQL:\n<lines until blank or next Q:>
      2. Markdown format (new):
         **Some question?**\n```kql\n<query>\n```\n
    Falls back to legacy parsing if markdown style not present.
    """
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()

    results: List[Dict[str, str]] = []

    md_question_pattern = re.compile(r"^\*\*(.+?)\*\*$")
    fence_start_pattern = re.compile(r"^```kql\s*$", re.IGNORECASE)
    fence_end_pattern = re.compile(r"^```\s*$")

    # First pass: markdown style
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        md_q_match = md_question_pattern.match(line)
        if md_q_match:
            question = md_q_match.group(1).strip()
            # Advance to kql fence
            j = i + 1
            while j < len(lines) and not fence_start_pattern.match(lines[j].strip()):
                j += 1
            if j >= len(lines):
                i = j
                continue  # no fenced block
            # Collect fenced query
            kql_lines: List[str] = []
            k = j + 1
            while k < len(lines) and not fence_end_pattern.match(lines[k].strip()):
                kql_lines.append(lines[k])
                k += 1
            # Only add if we found closing fence
            if k < len(lines):
                results.append({"question": question, "kql": "\n".join(kql_lines).strip()})
                i = k + 1
                continue
        i += 1

    if results:
        return results

    # Legacy fallback
    blocks = []
    i = 0
    current_q = None
    current_kql_lines: List[str] = []
    collecting = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.lower().startswith("q:"):
            if current_q and current_kql_lines:
                blocks.append({"question": current_q.strip(), "kql": "\n".join(current_kql_lines).strip()})
            current_q = stripped[2:].strip()
            current_kql_lines = []
            collecting = False
        elif stripped.lower().startswith("kql:"):
            collecting = True
        else:
            if collecting:
                if not stripped and (i + 1 < len(lines) and lines[i+1].strip().lower().startswith("q:")):
                    collecting = False
                else:
                    current_kql_lines.append(line)
        i += 1
    if current_q and current_kql_lines:
        blocks.append({"question": current_q.strip(), "kql": "\n".join(current_kql_lines).strip()})
    return blocks

def _select_relevant_fewshots(nl_question: str, examples: List[Dict[str, str]], top_k: int = 3) -> List[Dict[str, str]]:
    """Hybrid relevance selection combining heuristic & embedding similarity when available.

    Embeddings are attempted by default. Final score (if embeddings present):
      0.55 * heuristic_norm + 0.45 * cosine_sim.
    Falls back to heuristic-only if embedding call fails or returns None.
    """
    if not examples:
        return []
    q_low = nl_question.lower()

    typo_map = {"calcualte": "calculate", "latncy": "latency"}

    def normalize(token: str) -> str:
        return typo_map.get(token, token)

    def tokenize(text: str) -> List[str]:
        raw = [t for t in _re.split(r"[^a-z0-9]+", text.lower()) if t]
        return [normalize(t) for t in raw if len(t) > 1]

    q_tokens = set(tokenize(q_low))
    heuristic_records: List[Tuple[int, Dict[str, str]]] = []
    for ex in examples:
        q_ex = ex.get("question", "")
        q_ex_low = q_ex.lower()
        ex_tokens = set(tokenize(q_ex_low))
        h_score = 0
        if q_ex_low in q_low or q_low in q_ex_low:
            h_score += 10
        overlap = q_tokens.intersection(ex_tokens)
        h_score += len(overlap)
        for t in q_tokens:
            if any(_approx_close(t, et) for et in ex_tokens):
                h_score += 1
                break
        if ("workload" in ex_tokens and "workload" in q_tokens) or ("latency" in ex_tokens and "latency" in q_tokens):
            h_score += 2
        if ("pod" in ex_tokens or "pods" in ex_tokens) and ("pod" in q_tokens or "pods" in q_tokens):
            h_score += 2
        heuristic_records.append((h_score, ex))

    max_h = max((s for s, _ in heuristic_records), default=0)

    # Attempt embeddings
    try:
        embeddings = _maybe_embed_texts([nl_question] + [ex["question"] for _, ex in heuristic_records])
    except Exception:
        embeddings = None
    hybrid_rows: List[Tuple[float, Dict[str, str]]] = []
    if embeddings and len(embeddings) == len(heuristic_records) + 1:
        q_vec = embeddings[0]
        ex_vecs = embeddings[1:]
        for (h_score, ex), vec in zip(heuristic_records, ex_vecs):
            cosine_sim = _cosine(q_vec, vec)
            h_norm = (h_score / max_h) if max_h > 0 else 0.0
            final = 0.55 * h_norm + 0.45 * cosine_sim
            hybrid_rows.append((final, ex))
        hybrid_rows.sort(key=lambda x: x[0], reverse=True)
        selected = [ex for s, ex in hybrid_rows if s > 0][:top_k]
        if not selected:
            selected = [ex for _, ex in hybrid_rows[: min(2, len(hybrid_rows))]]
        print(f"[fewshot-select] embeddings_used=True max_h={max_h} top_scores={[round(s,4) for s,_ in hybrid_rows[:3]]}")
        return selected
    else:
        heuristic_records.sort(key=lambda x: x[0], reverse=True)
        selected = [ex for s, ex in heuristic_records if s > 0][:top_k]
        if not selected:
            selected = [ex for _, ex in heuristic_records[: min(2, len(heuristic_records))]]
        print(f"[fewshot-select] embeddings_used=False max_h={max_h} top_scores={[s for s,_ in heuristic_records[:3]]}")
        return selected

def _approx_close(a: str, b: str, max_dist: int = 2) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > max_dist:
        return False
    # Simple Levenshtein implementation (early exit)
    dp_prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        dp_curr = [i]
        min_row = dp_curr[0]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            dp_curr.append(min(
                dp_prev[j] + 1,      # deletion
                dp_curr[j-1] + 1,    # insertion
                dp_prev[j-1] + cost  # substitution
            ))
            if dp_curr[j] < min_row:
                min_row = dp_curr[j]
        dp_prev = dp_curr
        if min_row > max_dist:
            return False
    return dp_prev[-1] <= max_dist

def load_container_examples(nl_question: Optional[str] = None) -> Dict[str, str]:
    """Load container capsule, function signatures, and dynamically selected few-shots.

    If nl_question provided, perform relevance filtering to include only top matches.
    """
    root = os.path.dirname(os.path.abspath(__file__))
    # Relocated few-shots & capsule: prefer containers_capsule versions with fallback to legacy prompts
    # Updated few-shots location (markdown examples). Prefer new kql_examples file, fallback to old paths for compatibility.
    fewshots_path_primary = os.path.join(root, "containers_capsule", "kql_examples", "container_logs_kql_examples.md")
    fewshots_path_new = os.path.join(root, "containers_capsule", "fewshots_containerlogs.txt")  # deprecated legacy
    fewshots_path_legacy = os.path.join(root, "prompts", "fewshots_containerlogs.txt")  # original legacy
    if os.path.exists(fewshots_path_primary):
        fewshots_path = fewshots_path_primary
    elif os.path.exists(fewshots_path_new):
        fewshots_path = fewshots_path_new
    else:
        fewshots_path = fewshots_path_legacy

    capsule_path_new = os.path.join(root, "containers_capsule", "domain_capsule_containerlogs.txt")
    capsule_path_legacy = os.path.join(root, "prompts", "domain_capsule_containerlogs.txt")
    capsule_path = capsule_path_new if os.path.exists(capsule_path_new) else capsule_path_legacy
    # Prefer new top-level relocated capsule path; maintain backward compatibility fallbacks
    functions_path_new = os.path.join(root, "containers_capsule", "kql_functions_containerlogs.kql")
    functions_path_legacy = os.path.join(root, "docs", "containers_capsule", "kql_functions_containerlogs.kql")
    functions_path_old = os.path.join(root, "docs", "kql_functions_containerlogs.kql")
    if os.path.exists(functions_path_new):
        functions_path = functions_path_new
    elif os.path.exists(functions_path_legacy):
        functions_path = functions_path_legacy
    else:
        functions_path = functions_path_old

    examples_struct = _parse_container_fewshots(fewshots_path)
    selected_examples: List[Dict[str, str]] = []
    if nl_question:
        selected_examples = _select_relevant_fewshots(nl_question, examples_struct)
    # Format selected examples block
    if selected_examples:
        fewshots_block_parts = []
        for ex in selected_examples:
            fewshots_block_parts.append(f"Q: {ex['question']}\nKQL:\n{ex['kql']}")
        fewshots_block = "\n\n".join(fewshots_block_parts)
    else:
        # Fallback: include first ~1.4k chars of raw file (legacy)
        fewshots_block = _read_file(fewshots_path, limit=1400)

    capsule = _read_file(capsule_path, limit=800)
    functions_raw = _read_file(functions_path, limit=4000)
    fn_pairs = parse_container_function_signatures_with_docs(functions_raw)
    if fn_pairs:
        formatted = []
        for sig, desc in fn_pairs:
            line = f"- {sig}"
            if desc:
                line += f"  // {desc}"
            formatted.append(line)
        fn_list = "\n".join(formatted)
    else:
        fn_list = "(No function signatures)"
    return {
        "fewshots": fewshots_block,
        "capsule": capsule,
        "function_signatures": fn_list,
        "function_count": str(len(fn_pairs)),
        "selected_example_count": str(len(selected_examples)),
        "selected_examples_present": str(bool(selected_examples))
    }

def translate_nl_to_kql_enhanced(nl_question, max_retries=2):
    """Enhanced translation with actual multi-attempt retry and prompt slimming.

    Retry strategy:
      Attempt 0: full layered prompt.
      Attempt 1..N: slim prompt (remove capsule & function index, keep only top 1 few-shot) for same domain.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    nl_lower = nl_question.lower()
    if any(keyword in nl_lower for keyword in ["list tables", "show tables", "available tables", "tables available", "what tables"]):
        return """search *
| distinct $table
| order by $table asc"""
    if any(keyword in nl_lower for keyword in ["schema", "columns", "structure"]):
        table_keywords = ["apprequests", "appexceptions", "apptraces", "appdependencies", "apppageviews", "appcustomevents", "heartbeat", "usage"]
        mentioned_table = next((t.title() for t in table_keywords if t in nl_lower), None)
        return (f"{mentioned_table} | getschema | project ColumnName, ColumnType" if mentioned_table
                else "AppRequests | getschema | project ColumnName, ColumnType")

    last_error = None
    for attempt in range(max_retries):
        slim = attempt > 0
        result = _attempt_translation(nl_question, slim=slim)
        if not result.startswith("// Error"):
            if attempt > 0:
                print(f"[retry] succeeded on attempt {attempt} with slim={slim}")
            return result
        last_error = result
        print(f"[retry] attempt={attempt} failed: {result[:120]}")
    # Final fallback: attempt direct example reuse if domain is containers and we have a close example
    fallback = _example_fallback(nl_question)
    if fallback:
        return fallback
    return f"// Error: Could not translate question to KQL after retries: {nl_question}\n{last_error or ''}".strip()

def _attempt_translation(nl_question, slim: bool = False):
    print(f"🔍 Generating KQL for prompt: '{nl_question}'")
    
    # Load context from example files
    try:
        domain = detect_domain(nl_question)
    except ValueError as dom_exc:
        return f"// Error: {dom_exc}"  # Early exit with explicit domain classification error
    ctx = load_domain_context(domain, nl_question)
    
    # Build layered prompt (force KQL-only) then append domain-specific examples.
    layered_prompt, layered_meta = build_prompt(nl_question, force_kql_only=True)

    fewshots_text = ctx.get("fewshots", "")
    fn_text_full = ctx.get("function_signatures", "")
    capsule_full = ctx.get("capsule", "")

    # Initial assembly (non-slim)
    if slim:
        split_parts = fewshots_text.split("\n\n")
        slim_block = split_parts[0] if split_parts else fewshots_text
        examples_section = f"\n\nFewShot (slim domain={domain}):\n" + slim_block
        compression_meta = "slim=true"
    else:
        examples_section = (
            f"\n\nFewShotsSelected ({ctx.get('selected_example_count','0')}):\n" + fewshots_text +
            f"\n\nFunctionSignatures ({ctx.get('function_count','0')} detected):\n" + fn_text_full[:1000] +
            "\n\nCapsuleSummaryExcerpt:\n" + capsule_full[:600]
        )
        compression_meta = "slim=false"

    # ---------------- Token-based dynamic compression ---------------- #
    tentative_prompt = layered_prompt + examples_section
    TOKEN_LIMIT = int(os.getenv("PROMPT_TOKEN_LIMIT", "6000"))
    token_count = _count_tokens(tentative_prompt)
    compression_stage = "none"
    if token_count > TOKEN_LIMIT and not slim:
        # Stage 1: remove capsule entirely
        compression_stage = "capsule-removed"
        examples_section = (
            f"\n\nFewShotsSelected ({ctx.get('selected_example_count','0')}):\n" + fewshots_text +
            f"\n\nFunctionSignatures ({ctx.get('function_count','0')} detected):\n" + fn_text_full[:1200]
        )
        tentative_prompt = layered_prompt + examples_section
        token_count = _count_tokens(tentative_prompt)
    if token_count > TOKEN_LIMIT and not slim:
        # Stage 2: truncate function signatures
        compression_stage = compression_stage + "+fn-trunc"
        examples_section = (
            f"\n\nFewShotsSelected ({ctx.get('selected_example_count','0')}):\n" + fewshots_text +
            f"\n\nFunctionSignatures ({ctx.get('function_count','0')} detected, truncated):\n" + fn_text_full[:600]
        )
        tentative_prompt = layered_prompt + examples_section
        token_count = _count_tokens(tentative_prompt)
    if token_count > TOKEN_LIMIT and not slim:
        # Stage 3: truncate fewshots to first block
        compression_stage = compression_stage + "+fewshots-trunc"
        first_block = fewshots_text.split("\n\n")[0] if fewshots_text else ""
        examples_section = (
            f"\n\nFewShotPrimary ({ctx.get('selected_example_count','0')} total, truncated to 1):\n" + first_block +
            f"\n\nFunctionSignatures ({ctx.get('function_count','0')} detected, truncated):\n" + fn_text_full[:500]
        )
        tentative_prompt = layered_prompt + examples_section
        token_count = _count_tokens(tentative_prompt)
    if slim:
        compression_stage = "slim"
    compression_meta = f"token_limit={TOKEN_LIMIT} tokens={token_count} stage={compression_stage}"
    system_prompt = layered_prompt + examples_section + f"\n\n// prompt-meta {compression_meta} size_chars={len(layered_prompt + examples_section)}"
    # Debug: assert whether canonical example phrase present (case-insensitive)
    print(f"[prompt-debug] domain={domain} selected_examples={ctx.get('selected_example_count','0')} fn_count={ctx.get('function_count','0')}")
    print(f"[prompt] schema_version={layered_meta.get('schema_version')} output_mode={layered_meta.get('output_mode')} system_hash={layered_meta.get('system_hash')} fn_index_hash={layered_meta.get('function_index_hash')}")

    user_prompt = f"Question (domain={domain}): {nl_question}\nReturn ONLY the KQL query using appropriate tables for the {domain} domain."

    # Support legacy test monkeypatching: chat_completion may return tuple
    legacy_cfg = {
        "purpose": "translate",
        "allow_escalation": True,
        "debug_prefix": "Translate"
    }
    legacy_payload = {
        "system": system_prompt,
        "user": user_prompt
    }
    chat_out = chat_completion(legacy_cfg, legacy_payload)
    if isinstance(chat_out, tuple) and len(chat_out) >= 2:
        # Tuple protocol: (content, error, meta?, finish_reason?)
        raw_content, raw_error = chat_out[0], chat_out[1]
        class _TupleResult:
            def __init__(self, content, error):
                self.content = content
                self.error = error
        chat_res = _TupleResult(raw_content, raw_error)
    else:
        chat_res = chat_out

    # Emit structured event for translation (parity with explanation path)
    try:
        emit_chat_event(chat_res, extra={
            "phase": "translation",
            "domain": domain,
            "prompt_hash": stable_hash(layered_prompt),
            "fn_index_hash": layered_meta.get("function_index_hash"),
            "schema_version": layered_meta.get("schema_version"),
        })
    except Exception as log_exc:  # defensive, translation should not fail due to logging
        print(f"[translate] logging emit failed: {log_exc}")

    examples_included = ctx.get("selected_example_count") not in (None, "0")
    if chat_res.error:
        return f"// Error translating NL to KQL: {chat_res.error} [domain={domain} examples_included={examples_included} slim={slim}]"
    if not chat_res.content:
        return f"// Error: Empty or invalid response from AI [domain={domain} examples_included={examples_included} slim={slim}]"

    kql = chat_res.content.strip()
    
    # Clean up the response
    if kql.startswith("```kql"):
        kql = kql.replace("```kql", "").replace("```", "").strip()
    elif kql.startswith("```") and kql.endswith("```"):
        kql = kql.strip('`').strip()
    
    # Basic validation - check if it looks like a valid KQL query
    if not kql or len(kql.strip()) < 5:
        return f"// Error: Empty or invalid response from AI [domain={domain} examples_included={examples_included} slim={slim}]"
    
    # Check for invalid starting characters
    if kql.strip().startswith('.'):
        return "// Error: Invalid KQL query starting with '.'"
    
    # Check for common error indicators
    error_indicators = ["sorry", "cannot", "unable", "error", "apologize"]
    if any(indicator in kql.lower() for indicator in error_indicators):
        return f"// Error: AI returned error response: {kql} [domain={domain} examples_included={examples_included} slim={slim}]"
    
    # Successful translation; prepend structured telemetry meta as comment
    meta_prefix = f"// meta: domain={domain} slim={slim} examples_included={examples_included} selected_examples={ctx.get('selected_example_count','0')} {compression_meta}\n"
    return meta_prefix + kql

def _example_fallback(nl_question: str) -> Optional[str]:
    """If translation failed, attempt to return top matching example KQL.

    Strategy: reuse relevance selection; if first example shares >=2 tokens with query, return it.
    """
    try:
        domain = detect_domain(nl_question)
    except Exception:
        return None
    ctx = load_domain_context(domain, nl_question)
    fewshots_raw = ctx.get("fewshots", "")
    # Parse back examples from block format (Q: ...\nKQL:) for reliability
    pattern = re.compile(r"Q:\s*(.+?)\nKQL:\n(.*?)(?=(\n\nQ:|$))", re.DOTALL)
    matches = pattern.findall(fewshots_raw)
    if not matches:
        return None
    q_low = nl_question.lower()
    def score_example(q_text: str) -> int:
        q_tokens = {t for t in re.split(r"[^a-z0-9]+", q_low) if t}
        ex_tokens = {t for t in re.split(r"[^a-z0-9]+", q_text.lower()) if t}
        return len(q_tokens & ex_tokens) + (10 if q_text.lower() in q_low or q_low in q_text.lower() else 0)
    ranked = sorted(matches, key=lambda m: score_example(m[0]), reverse=True)
    best_q, best_kql = ranked[0][0], ranked[0][1].strip()
    if score_example(best_q) < 2:
        return None
    return f"// meta: domain={domain} fallback=example reused_question='{best_q}'\n" + best_kql

if __name__ == "__main__":
    # Test the enhanced translation
    test_questions = [
        "what are the top 5 slowest API calls?",
        "show me failed requests from the last hour", 
        "get exceptions from today",
        "show me request duration over time"
    ]
    
    print("🧪 Testing Enhanced NL to KQL Translation")
    print("=" * 50)
    
    for question in test_questions:
        print(f"\n❓ Question: {question}")
        result = translate_nl_to_kql_enhanced(question)
        print(f"📝 KQL: {result}")
        print("-" * 30)
