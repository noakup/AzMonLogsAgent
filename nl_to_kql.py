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
    create_embeddings,
)

# ---------------- Intent Extraction & Enforcement (A-C) ---------------- #
_TIME_REGEX = re.compile(r"(last|past)\s+(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks)", re.IGNORECASE)
_SINGULAR_MAP = {
    "minutes": "m", "minute": "m",
    "hours": "h", "hour": "h",
    "days": "d", "day": "d",
    "weeks": "d"  # convert weeks -> days (approx, 1 week -> 7d later)
}

def _extract_time_and_metric_intent(nl_question: str) -> Dict[str, str]:
    """Parse timeframe & metric intent from natural language.

    Returns dict keys:
      timeframe_window: e.g. '1d', '30m', '' if unspecified
      timeframe_phrase: original matched phrase or heuristic
      metric_mode: 'count' | 'rate' | 'duration' | 'unknown'
      raw_metric_hint: matched keyword triggering metric_mode
    Heuristics:
      - 'last X <unit>' explicit regex
      - 'today' -> 1d, 'yesterday' -> 1d (different day but treat as day scope)
      - 'last hour' / 'past hour' etc.
      - Metric keywords: count(number,total,"how many"), rate(rate, per second, throughput, percent, percentage, ratio), duration(latency, duration, time taken, response time)
    """
    lower = nl_question.lower()
    timeframe_window = ''
    timeframe_phrase = ''
    m = _TIME_REGEX.search(lower)
    if m:
        qty = int(m.group(2))
        unit = m.group(3).lower()
        # weeks -> qty*7 days
        if unit.startswith('week'):
            qty = qty * 7
            unit = 'day'
        suffix = _SINGULAR_MAP.get(unit, '')
        if suffix:
            timeframe_window = f"{qty}{suffix}"
            timeframe_phrase = m.group(0)
    else:
        # Simple heuristics
        if 'last hour' in lower or 'past hour' in lower:
            timeframe_window, timeframe_phrase = '1h', 'last hour'
        elif 'last day' in lower or 'past day' in lower or 'today' in lower:
            timeframe_window, timeframe_phrase = '1d', 'last day'
        elif 'last 30 minutes' in lower or 'past 30 minutes' in lower:
            timeframe_window, timeframe_phrase = '30m', 'last 30 minutes'

    metric_mode = 'unknown'
    raw_metric_hint = ''
    # Order matters: count before rate to respect 'error count' vs 'error rate'
    count_terms = ['count', 'number', 'total', 'how many']
    rate_terms = ['rate', 'per second', 'throughput', 'percent', 'percentage', 'ratio']
    duration_terms = ['duration', 'latency', 'time taken', 'response time']
    for term in count_terms:
        if term in lower:
            metric_mode = 'count'
            raw_metric_hint = term
            break
    if metric_mode == 'unknown':
        for term in rate_terms:
            if term in lower:
                metric_mode = 'rate'
                raw_metric_hint = term
                break
    if metric_mode == 'unknown':
        for term in duration_terms:
            if term in lower:
                metric_mode = 'duration'
                raw_metric_hint = term
                break
    # Disambiguation: if both 'error rate' and 'error count' present pick last explicit
    if 'error count' in lower:
        metric_mode = 'count'
        raw_metric_hint = 'error count'
    elif 'error rate' in lower and metric_mode != 'count':
        metric_mode = 'rate'
        raw_metric_hint = 'error rate'

    return {
        'timeframe_window': timeframe_window,
        'timeframe_phrase': timeframe_phrase,
        'metric_mode': metric_mode,
        'raw_metric_hint': raw_metric_hint
    }

# _AGO_REGEX = re.compile(r"ago\((\d+)([mhd])\)")


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

def _embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    """Return list of embedding vectors or None if unavailable.
    Attempts to obtain embeddings.
    """
    try:
        vectors = create_embeddings(texts)
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
        return load_container_shots(nl_question)

    # Application Insights domain processing
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
        # top_k now sourced internally from FEWSHOT_TOP_K env var (default 4)
        selected = _select_relevant_fewshots(nl_question, parsed_examples)
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

    capsule_path = "app_insights_capsule/README.md"
    capsule_excerpt = _read_file(capsule_path, limit=600) if os.path.exists(capsule_path) else "(No capsule)"
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
    # Determine domain for natural language question.
    # Returns 'containers' or 'appinsights'; raises ValueError if no indicators found.
    q = nl_question.lower()
    matched_container = {kw for kw in CONTAINER_KEYWORDS if kw in q}
    matched_app = {kw for kw in APPINSIGHTS_KEYWORDS if kw in q}

    if _CONTAINER_TABLE_REGEX.search(q):
        matched_container.add("<table-match>")
    if _APP_TABLE_REGEX.search(q):
        matched_app.add("<table-match>")
    if ("pod" in q or "pods" in q) and "pending" in q:
        matched_container.add("<pods-pending>")

    print(f"[domain-detect] q='{nl_question}' container_matches={sorted(matched_container)} app_matches={sorted(matched_app)}")

    if matched_container and not matched_app:
        print("[domain-detect] chosen=containers (exclusive container matches)")
        return "containers"
    if matched_app and not matched_container:
        print("[domain-detect] chosen=appinsights (exclusive app matches)")
        return "appinsights"
    if matched_container and matched_app:
        if any(sig in matched_container for sig in ("<table-match>", "<pods-pending>")):
            print("[domain-detect] chosen=containers (conflict; container strong signal)")
            return "containers"
        print("[domain-detect] chosen=appinsights (conflict; default to appinsights)")
        return "appinsights"

    raise ValueError("Unable to classify domain. Include explicit indicators like 'pod', 'containerlogv2', 'request', or 'apprequests'.")

def _read_file(path: str, limit: int = 1600) -> str:
    if not os.path.exists(path):
        return "File not found"
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    if len(data) > limit:
        return data[:limit] + "..."
    return data

def parse_container_function_signatures(kql_text: str) -> List[str]:
    # Backward-compatible thin wrapper returning only signature strings.
    # Internally uses the richer parser with descriptions.
    return [s for s, _ in parse_container_function_signatures_with_docs(kql_text)]

def parse_container_function_signatures_with_docs(kql_text: str) -> List[Tuple[str, str]]:
    # Parse function signatures with brief description (taken from preceding // comment).
    # Supports multi-line declarations of the form:
    #   let FuncName =\n    (Param1:type, Param2:type)\n    {
    # or single-line: let FuncName = (Param1:type){
    # Returns list of tuples: ("FuncName(paramlist)", "Description or empty").
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

def _parse_container_csv_shots(path: str) -> List[Dict[str, str]]:
    """Parse container examples from a CSV file with columns (Prompt, Query).

    Supports multi-line KQL queries enclosed in quotes. Minimal validation:
      - Skips rows where prompt or query is empty.
      - Normalizes Windows CRLF line endings.
    """
    if not os.path.exists(path):
        return []
    results: List[Dict[str, str]] = []
    try:
        import csv
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header: List[str] = []
            first = True
            for row in reader:
                # Detect header row
                if first:
                    header = [h.strip().lower() for h in row]
                    first = False
                    # If header matches expected, continue to next row
                    if set(header) >= {"prompt", "query"}:
                        continue
                    else:
                        # Treat first row as data if header not recognized
                        header = []
                if not row or len(row) < 2:
                    continue
                prompt = row[0].strip()
                query = row[1].strip()
                if not prompt or not query:
                    continue
                # Normalize embedded double-double quotes that represent escaped quotes
                query = query.replace('""', '"')
                results.append({"question": prompt, "kql": query})
    except Exception as csv_exc:
        print(f"[csv-parse] failed path={path} error={csv_exc}")
    return results

def _select_relevant_fewshots(nl_question: str, examples: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Select relevant few-shot examples.

    top_k now driven by environment variable FEWSHOT_TOP_K (default=4).
    Try persistent index (embedding_index.select_with_index).
    Raises RuntimeError if embeddings explicitly required and unavailable (legacy behavior retained).
    """
    if not examples:
        return []
    try:
        top_k_env = int(os.getenv("FEWSHOT_TOP_K", "4"))
    except ValueError:
        top_k_env = 4
    top_k = max(1, min(top_k_env, 12))  # guardrails
    # Attempt indexed selection (import deferred to avoid circular during startup)
    try:
        from embedding_index import select_with_index  # type: ignore
        # We don't know domain here directly; caller supplies examples already domain-specific.
        # Heuristic: infer domain by presence of canonical table tokens in example KQL.
        domain_guess = "containers"
        sample_text = "\n".join(ex.get("kql", "") for ex in examples[:4]).lower()
        if any(tok in sample_text for tok in ["apprequests", "apptraces", "appexceptions", "appdependencies"]):
            domain_guess = "appinsights"
        indexed = select_with_index(nl_question, examples, domain_guess, top_k=top_k)
        if indexed:
            print(f"[fewshot-select] used_index=True domain={domain_guess} returned={len(indexed)}")
            return indexed
    except Exception as idx_exc:
        print(f"[fewshot-select] index_unavailable fallback_legacy error={idx_exc}")

    # Legacy path
    q_low = nl_question.lower()

    def tokenize(text: str) -> List[str]:
        return [t for t in _re.split(r"[^a-z0-9]+", text.lower()) if t]
        
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

    # Apply embeddings
    # Logging embedding input set (question + candidate example questions)
    try:
        _embed_inputs_preview = [nl_question] + [ex["question"] for _, ex in heuristic_records]
        print("[embed-inputs] total_inputs=" + str(len(_embed_inputs_preview)) +
              " preview=" + json.dumps(_embed_inputs_preview[:8], ensure_ascii=False)[:800])
    except Exception as _embed_log_exc:  # defensive; never block selection
        print(f"[embed-inputs] logging_failed error={_embed_log_exc}")
    try:
        embeddings = _embed_texts([nl_question] + [ex["question"] for _, ex in heuristic_records])
    except Exception as embed_exc:
        print(f"[fewshot-select] embedding_exception={embed_exc}")
        embeddings = None
    if (not embeddings or len(embeddings) != len(heuristic_records) + 1):
        # no embeddings -> raise explicit error to caller for deterministic failure.
        raise RuntimeError("Embeddings required but unavailable.")
    
    hybrid_rows: List[Tuple[float, Dict[str, str]]] = []

    q_vec = embeddings[0]
    ex_vecs = embeddings[1:]
    for (h_score, ex), vec in zip(heuristic_records, ex_vecs):
        cosine_sim = _cosine(q_vec, vec)
        h_norm = (h_score / max_h) if max_h > 0 else 0.0
        final = 0.55 * h_norm + 0.45 * cosine_sim
        hybrid_rows.append((final, ex))
    hybrid_rows.sort(key=lambda x: x[0], reverse=True)
    best_matching_examples = [ex for s, ex in hybrid_rows if s > 0][:top_k]
    if not best_matching_examples:
        best_matching_examples = [ex for _, ex in hybrid_rows[: min(2, len(hybrid_rows))]]
    print(f"[fewshot-select] embeddings_used=True (legacy) max_h={max_h} top_scores={[round(s,4) for s,_ in hybrid_rows[:3]]}")
    return best_matching_examples

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

def load_container_shots(nl_question: Optional[str] = None) -> Dict[str, str]:
    """Load container shots (CSV only) without duplicating capsule or function signatures.

    Rules:
      - Do NOT return capsule/function signature text (already included via build_prompt).
      - If no relevant selected examples found (selection empty), return an error indicator and no fallback examples.
    """
    root = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(root, "containers_capsule", "public_shots.csv")
    if os.path.exists(csv_path):
        public_shots_struct = _parse_container_csv_shots(csv_path)
        print(f"[container-public_shots] source=csv path={csv_path} count={len(public_shots_struct)}")
    else:
        print(f"[container-public_shots] WARNING: CSV examples file missing at {csv_path}; proceeding with empty examples list")
        public_shots_struct = []
    selected_shots: List[Dict[str, str]] = []
    if nl_question and public_shots_struct:
        selected_shots = _select_relevant_fewshots(nl_question, public_shots_struct)

    if selected_shots:
        fewshots_block = "\n\n".join(
            [f"Q: {ex['question']}\nKQL:\n{ex['kql']}" for ex in selected_shots]
        )
    else:
        fewshots_block = ""
        examples_error = "No relevant container examples selected (index empty or low relevance)."
        # Compute top candidate scores (cosine only) for diagnostics if embeddings available
        top_scores: List[Tuple[float, str]] = []
        try:
            if public_shots_struct and nl_question:
                questions = [nl_question] + [ex['question'] for ex in public_shots_struct]
                vecs = _embed_texts(questions)
                if vecs and len(vecs) == len(questions):
                    q_vec = vecs[0]
                    ex_vecs = vecs[1:]
                    scored: List[Tuple[float, str]] = []
                    for ex, v in zip(public_shots_struct, ex_vecs):
                        score = _cosine(q_vec, v)
                        scored.append((score, ex['question']))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    top_scores = scored[:5]
        except Exception as diag_exc:
            print(f"[container-examples] candidate-score-diagnostics failed error={diag_exc}")
        # Log diagnostic summary
        if top_scores:
            printable = [round(s,4) for s,_ in top_scores]
            print(f"[container-examples] no-selection error='{examples_error}' top_candidate_scores={printable} total_available={len(public_shots_struct)}")
        else:
            print(f"[container-examples] no-selection error='{examples_error}' top_candidate_scores=[] total_available={len(public_shots_struct)}")
        return {
            "fewshots": fewshots_block,
            "capsule": "",  # suppressed
            "function_signatures": "",  # suppressed
            "function_count": "0",
            "selected_example_count": "0",
            "selected_examples_present": "False",
            "examples_error": examples_error,
            "top_candidate_scores": json.dumps([{"score": round(s,6), "question": q} for s, q in top_scores])
        }

    return {
        "fewshots": fewshots_block,
        "capsule": "",  # suppress duplicate capsule
        "function_signatures": "",  # suppress duplicate functions
        "function_count": "0",
        "selected_example_count": str(len(selected_shots)),
        "selected_examples_present": str(bool(selected_shots)),
        "top_candidate_scores": ""  # intentionally empty when selection succeeded
    }

def translate_nl_to_kql(nl_question, max_retries=2):
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
        use_slim_prompt = attempt > 0
        result = _attempt_translation(nl_question, use_slim_prompt)
        if not result.startswith("// Error"):
            print(f"[retry] succeeded on attempt {attempt} with slim_prompt={use_slim_prompt}")
            return result
        last_error = result
        print(f"[retry] attempt={attempt} failed: {result[:240]}")
    
    return f"// Error: Could not translate question to KQL after retries: {nl_question}\n{last_error or ''}".strip()

def _attempt_translation(nl_question, use_slim_prompt: bool = False):
    print(f"🔍 Generating KQL for prompt: '{nl_question}'")
    # Align naming with existing internal references expecting 'slim_prompt'
    slim_prompt = use_slim_prompt
    
    # Load context from example files
    try:
        domain = detect_domain(nl_question)
    except ValueError as dom_exc:
        return f"// Error: {dom_exc}"  # Early exit with explicit domain classification error
    try:
        ctx = load_domain_context(domain, nl_question)
    except RuntimeError as embed_exc:
        # Hard enforcement failure (e.g., REQUIRE_EMBEDDINGS=1 but embeddings unavailable)
        return f"// Error: {embed_exc}"

    # Early abort for containers domain if no selected examples (per new rule)
    if domain == "containers" and ctx.get("selected_example_count") == "0":
        err_msg = ctx.get("examples_error", "No relevant container examples available.")
        # Emit telemetry event before returning to surface examples_error
        try:
            emit_chat_event(None, extra={
                "phase": "translation-abort",
                "domain": domain,
                "examples_error": err_msg,
                "selected_example_count": ctx.get("selected_example_count"),
            })
        except Exception as log_exc:
            print(f"[translate-abort] logging emit failed: {log_exc}")
        return f"// Error: {err_msg} [domain=containers selected_example_count=0]"
    
    # Build layered prompt (force KQL-only) then append domain-specific examples.
    layered_prompt, layered_meta = build_prompt(nl_question, force_kql_only=True)

    fewshots_text = ctx.get("fewshots", "")
    fn_text_full = ctx.get("function_signatures", "")
    capsule_full = ctx.get("capsule", "")

    # Initial assembly (non-slim prompt)
    if slim_prompt:
        split_parts = fewshots_text.split("\n\n")
        slim_block = split_parts[0] if split_parts else fewshots_text
        examples_section = f"\n\nFewShot (slim for domain={domain}):\n" + slim_block
        compression_meta = "slim_prompt=true"
    else:
        examples_section = (
            f"\n\nFewShotsSelected ({ctx.get('selected_example_count','0')}):\n" + fewshots_text +
            f"\n\nFunctionSignatures ({ctx.get('function_count','0')} detected):\n" + fn_text_full[:1000] +
            "\n\nCapsuleSummaryExcerpt:\n" + capsule_full[:600]
        )
        compression_meta = "slim_prompt=false"

    # ---------------- Token-based dynamic compression ---------------- #
    tentative_prompt = layered_prompt + examples_section
    TOKEN_LIMIT = int(os.getenv("PROMPT_TOKEN_LIMIT", "4000"))
    token_count = _count_tokens(tentative_prompt)
    compression_stage = "none"
    if token_count > TOKEN_LIMIT and not slim_prompt:
        # Stage 1: remove capsule entirely
        compression_stage = "capsule-removed"
        examples_section = (
            f"\n\nFewShotsSelected ({ctx.get('selected_example_count','0')}):\n" + fewshots_text +
            f"\n\nFunctionSignatures ({ctx.get('function_count','0')} detected):\n" + fn_text_full[:1200]
        )
        tentative_prompt = layered_prompt + examples_section
        token_count = _count_tokens(tentative_prompt)
    if token_count > TOKEN_LIMIT and not slim_prompt:
        # Stage 2: truncate function signatures
        compression_stage = compression_stage + "+fn-trunc"
        examples_section = (
            f"\n\nFewShotsSelected ({ctx.get('selected_example_count','0')}):\n" + fewshots_text +
            f"\n\nFunctionSignatures ({ctx.get('function_count','0')} detected, truncated):\n" + fn_text_full[:600]
        )
        tentative_prompt = layered_prompt + examples_section
        token_count = _count_tokens(tentative_prompt)
    if token_count > TOKEN_LIMIT and not slim_prompt:
        # Stage 3: truncate fewshots to first block
        compression_stage = compression_stage + "+fewshots-trunc"
        first_block = fewshots_text.split("\n\n")[0] if fewshots_text else ""
        examples_section = (
            f"\n\nFewShotPrimary ({ctx.get('selected_example_count','0')} total, truncated to 1):\n" + first_block +
            f"\n\nFunctionSignatures ({ctx.get('function_count','0')} detected, truncated):\n" + fn_text_full[:500]
        )
        tentative_prompt = layered_prompt + examples_section
        token_count = _count_tokens(tentative_prompt)
    if slim_prompt:
        compression_stage = "slim_prompt"
    compression_meta = f"token_limit={TOKEN_LIMIT} tokens={token_count} stage={compression_stage}"
    # (A) Extract intent, (B) inject directive into system prompt before final meta
    #_intent = _extract_time_and_metric_intent(nl_question)
    system_prompt_core = layered_prompt + examples_section
    system_prompt = system_prompt_core + f"\n\n// prompt-meta {compression_meta} size_chars={len(system_prompt_core)}"
    # Log full layered prompt (truncated) for debugging prompt construction
    try:
        _prompt_tokens_est = _count_tokens(system_prompt)
        _prompt_preview = system_prompt[:1500]
        if len(system_prompt) > 1500:
            _prompt_preview += "...(truncated)"
        print(f"[full-prompt] slim_prompt={slim_prompt} chars={len(system_prompt)} tokens~={_prompt_tokens_est} preview_start={json.dumps(_prompt_preview)[:1600]}")
    except Exception as _prompt_log_exc:
        print(f"[full-prompt] logging_failed error={_prompt_log_exc}")
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
            "selected_example_count": ctx.get("selected_example_count"),
            "examples_error": ctx.get("examples_error"),
        })
    except Exception as log_exc:  # defensive, translation should not fail due to logging
        print(f"[translate] logging emit failed: {log_exc}")

    examples_included = ctx.get("selected_example_count") not in (None, "0")
    if chat_res.error:
        return f"// Error translating NL to KQL: {chat_res.error} [domain={domain} examples_included={examples_included} slim_prompt={slim_prompt}]"
    if not chat_res.content:
        return f"// Error: Empty or invalid response from AI [domain={domain} examples_included={examples_included} slim_prompt={slim_prompt}]"

    kql = chat_res.content.strip()
    
    # Clean up the response
    if kql.startswith("```kql"):
        kql = kql.replace("```kql", "").replace("```", "").strip()
    elif kql.startswith("```") and kql.endswith("```"):
        kql = kql.strip('`').strip()
    
    # Basic validation - check if it looks like a valid KQL query
    if not kql or len(kql.strip()) < 5:
        return f"// Error: Empty or invalid response from AI [domain={domain} examples_included={examples_included} slim_prompt={slim_prompt}]"
    
    # Check for invalid starting characters
    if kql.strip().startswith('.'):
        return "// Error: Invalid KQL query starting with '.'"
    
    # Check for common error indicators
    # Refined error heuristics: avoid treating legitimate 'Error' token filters as failures.
    content_lower = kql.lower()
    error_phrases = [
        "an error occurred", "error: ", "unable to", "cannot ", "can't ",
        "i cannot", "i can't", "sorry", "apologize", "could not"
    ]
    if any(p in content_lower for p in error_phrases):
        return f"// Error: AI returned error response: {kql} [domain={domain} examples_included={examples_included} slim_prompt={slim_prompt}]"
    
    # Successful translation; prepend structured telemetry meta as comment
    # Intent enforcement removed per user request (was corrupting generated KQL).
    meta_prefix = f"// meta: domain={domain} slim_prompt={slim_prompt} examples_included={examples_included} selected_examples={ctx.get('selected_example_count','0')} {compression_meta}\n"
    return meta_prefix + kql

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
        result = translate_nl_to_kql(question)
        print(f"📝 KQL: {result}")
        print("-" * 30)
