"""Shared Azure OpenAI helper utilities to centralize configuration, version selection,
payload construction, and URL building for both translation and explanation paths.
"""
from __future__ import annotations
import os
import re
from typing import Dict, Tuple, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
import json
import time
import requests
import hashlib
from datetime import datetime, UTC

try:  # Optional dependency; don't fail if missing
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

DEFAULT_STANDARD_API_VERSION = "2024-09-01-preview"
DEFAULT_O_MODELS_API_VERSION = "2024-12-01-preview"

# ---------------------------------------------------------------------------
# API Version Selection (Item 1)
# ---------------------------------------------------------------------------
def select_api_version(deployment: str, api_version_override: Optional[str]) -> Tuple[str, bool]:
    """Return (api_version, is_override) based on override env or deployment family.

    Extraction from load_config for testability and clarity.
    """
    if api_version_override:
        return api_version_override, True
    if _is_o_model(deployment):
        return DEFAULT_O_MODELS_API_VERSION, False
    return DEFAULT_STANDARD_API_VERSION, False

class AzureOpenAIConfig:
    def __init__(self, endpoint: str, api_key: str, deployment: str, api_version: str, is_override: bool,
                 embedding_endpoint: str, embedding_model: str, embedding_deployment: str, embedding_api_version: str, embedding_api_key: str):
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment = deployment
        self.api_version = api_version
        self.is_override = is_override
        self.embedding_endpoint = embedding_endpoint
        self.embedding_model = embedding_model
        self.embedding_deployment = embedding_deployment
        self.embedding_api_version = embedding_api_version
        self.embedding_api_key = embedding_api_key

    def base_url(self) -> str:
        return f"{self.endpoint}/openai/deployments/{self.deployment}"

    def chat_completions_url(self) -> str:
        print(f"[debug:] Chat completions URL: {self.base_url()}/chat/completions?api-version={self.api_version}")
        return f"{self.base_url()}/chat/completions?api-version={self.api_version}"

def load_config() -> AzureOpenAIConfig | None:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    print(f"[debug:] Loaded AZURE_OPENAI_ENDPOINT: {endpoint}")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
    print(f"[debug:] Loaded AZURE_OPENAI_DEPLOYMENT: {deployment}")
    api_version_override = os.environ.get("AZURE_OPENAI_API_VERSION")
    print(f"[debug:] Loaded AZURE_OPENAI_API_VERSION: {api_version_override}")
    # --- embeddings config ---
    embedding_endpoint = os.environ.get("AZURE_OPENAI_EMBEDDING_ENDPOINT")
    print(f"[debug:] Loaded AZURE_OPENAI_EMBEDDING_ENDPOINT: {embedding_endpoint}")
    embedding_model = os.environ.get("AZURE_OPENAI_EMBEDDING_MODEL")
    print(f"[debug:] Loaded AZURE_OPENAI_EMBEDDING_MODEL: {embedding_model}")
    embedding_deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    print(f"[debug:] Loaded AZURE_OPENAI_EMBEDDING_DEPLOYMENT: {embedding_deployment}")
    embedding_api_version = os.environ.get("AZURE_OPENAI_EMBEDDING_API_VERSION")
    print(f"[debug:] Loaded AZURE_OPENAI_EMBEDDING_API_VERSION: {embedding_api_version}")
    embedding_api_key = os.environ.get("AZURE_OPENAI_EMBEDDING_API_KEY")

    if not endpoint or not api_key:
        print("[debug:] Missing endpoint or API key in environment variables.")
        return None

    if not endpoint.startswith("http"):
        endpoint = f"https://{endpoint}"
    endpoint = endpoint.rstrip('/')

    api_version, is_override = select_api_version(deployment, api_version_override)
    if is_override:
        print(f"[debug:] Using overridden API version: {api_version}")
    else:
        print(f"[debug:] Selected API version: {api_version} (o-model={_is_o_model(deployment)})")

    return AzureOpenAIConfig(endpoint, api_key, deployment, api_version, is_override, embedding_endpoint, embedding_model, embedding_deployment, embedding_api_version, embedding_api_key)

def _is_o_model(deployment: str) -> bool:
    """Return True only for explicitly named o-model family deployments.

    We intentionally avoid matching generic 'gpt-4o' (the mainstream 4o models)
    because they use the standard chat payload shape. We treat as o-model only if
    the deployment name clearly starts with one of the specialized research/optimized
    families like 'o1', 'o1-', 'o4', 'o4-'. Case-insensitive.
    """
    if not deployment:
        return False
    d = deployment.lower()
    return d == "o1" or d == "o4" or d.startswith("o1-") or d.startswith("o4-")

def build_payload(messages: list[Dict[str, str]], *, is_o_model: bool, max_output_tokens: int = 500, temperature: float | None = 0.3, top_p: float | None = 0.9) -> Dict[str, Any]:
    """Return a properly shaped payload for Azure OpenAI Chat Completions.

    For o-models (o1, o4 families) only user messages are supported and use max_completion_tokens.
    For standard models we support temperature, top_p, etc.
    """
    if is_o_model:
        # Combine messages into a single user message
        combined_content = "\n\n".join(m.get("content", "") for m in messages)
        return {
            "messages": [
                {"role": "user", "content": combined_content}
            ],
            "max_completion_tokens": max_output_tokens
        }
    # Standard model
    payload: Dict[str, Any] = {
        "messages": messages,
        "max_tokens": max_output_tokens
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    return payload

def mask_key(k: str | None) -> str:
    if not k:
        return ""
    return f"{k[:4]}***len={len(k)}"

def debug_print_config(prefix: str, cfg: AzureOpenAIConfig):
    try:
        print(f"[{prefix}] Endpoint: {cfg.endpoint}")
        print(f"[{prefix}] Deployment: {cfg.deployment}")
        print(f"[{prefix}] API Version: {cfg.api_version} (override={'YES' if cfg.is_override else 'NO'})")
        print(f"[{prefix}] API Key Present: {'YES' if cfg.api_key else 'NO'} ({mask_key(cfg.api_key)})")
        print(f"[{prefix}] Embedding Endpoint: {cfg.embedding_endpoint}")
        print(f"[{prefix}] Embedding Model: {cfg.embedding_model}")
        print(f"[{prefix}] Embedding Deployment: {cfg.embedding_deployment}")
        print(f"[{prefix}] Embedding API Version: {cfg.embedding_api_version}")
        print(f"[{prefix}] Embedding API Key Present: {'YES' if cfg.embedding_api_key else 'NO'} ({mask_key(cfg.embedding_api_key)})")
    except Exception as e:
        print(f"[{prefix}] Failed to print config: {e}")

def get_env_int(name: str, default: int, min_value: int | None = None, max_value: int | None = None) -> int:
    """Fetch an integer environment variable with validation and fallback."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        val = int(raw)
        if min_value is not None and val < min_value:
            return default
        if max_value is not None and val > max_value:
            return default
        return val
    except ValueError:
        return default

# === Shared Chat Helper Layer (restored) ===

def build_messages(system_prompt: str, user_prompt: str, *, is_o_model: bool) -> List[Dict[str, str]]:
    """Return message list formatted per model type."""
    if is_o_model:
        print(f"[debug:] {{\"role\":\"user\", \"content\":\"{system_prompt}\n\n{user_prompt}\"}}")
        return [{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}]
    print(f"[debug:] {{\"role\":\"system\", \"content\":\"{system_prompt}\"}}")
    print(f"[debug:] {{\"role\":\"user\", \"content\":\"{user_prompt}\"}}")
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

def build_chat_request(
    messages: List[Dict[str, str]],
    *,
    is_o_model: bool,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
) -> Dict[str, Any]:
    """Return chat request payload with optional overrides.

    Backwards compatible: if overrides not provided, env/defaults are used.
    """
    # Default increased from 500 -> 1000 to allow more reasoning/output without requiring env override.
    env_max = get_env_int("AZURE_OPENAI_MAX_OUTPUT_TOKENS", 2000, min_value=50, max_value=4000)
    out_tokens = max_tokens if max_tokens is not None else env_max
    if is_o_model:
        return build_payload(messages, is_o_model=True, max_output_tokens=out_tokens)
    base_temp_default = float(os.environ.get("AZURE_OPENAI_TRANSLATE_BASE_TEMP", "0.1"))
    eff_temp = base_temp_default if temperature is None else temperature
    eff_top_p = 0.9 if top_p is None else top_p
    return build_payload(messages, is_o_model=False, max_output_tokens=out_tokens, temperature=eff_temp, top_p=eff_top_p)


def chat_completion(cfg: AzureOpenAIConfig, payload: Dict[str, Any], *, max_retries: int = 3, base_delay: float = 1.0, timeout: int = 30, debug_prefix: str = "Chat") -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]], Optional[str]]:
    """Execute chat completion with retries.

    Returns (content, error_message, raw_json, finish_reason)
    """
    url = cfg.chat_completions_url()
    print(f"[debug {debug_prefix}] URL: {url}")
    headers = {"Content-Type": "application/json", "api-key": cfg.api_key}
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
            if resp.status_code == 429 and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"[{debug_prefix}] 429 rate limit; retrying in {delay}s")
                time.sleep(delay)
                continue
            if resp.status_code == 401:
                return None, "Authentication failed (401)", None, None
            if resp.status_code == 404:
                return None, f"Deployment not found (404): {cfg.deployment}", None, None
            if resp.status_code == 400:
                print(f"[{debug_prefix}] 400 body snippet: {resp.text[:400] if hasattr(resp,'text') else ''}")
            resp.raise_for_status()
            try:
                data = resp.json()
            except json.JSONDecodeError:
                return None, "Invalid JSON response", None, None
            if 'error' in data:
                return None, data['error'].get('message', 'Unknown API error'), data, None
            if 'choices' not in data or not data['choices']:
                return None, "No choices returned", data, None
            choice = data['choices'][0]
            if choice.get('finish_reason') == 'content_filter':
                return None, "Response filtered (content policy)", data, choice.get('finish_reason')
            msg = choice.get('message', {})
            content_field = msg.get('content')
            extracted_text = ""
            # Azure sometimes returns a list of content parts; handle string or list
            if isinstance(content_field, str):
                extracted_text = content_field
            elif isinstance(content_field, list):
                parts: List[str] = []
                for part in content_field:
                    # Common shapes: {"type":"text","text":"..."} or direct strings
                    if isinstance(part, str):
                        if part.strip():
                            parts.append(part.strip())
                    elif isinstance(part, dict):
                        txt = part.get('text') or part.get('content') or ''
                        if isinstance(txt, str) and txt.strip():
                            parts.append(txt.strip())
                extracted_text = "\n".join(p for p in parts if p)
            # Fallback: attempt to pull from alternative keys
            if not extracted_text:
                alt = msg.get('alternate') or msg.get('response')
                if isinstance(alt, str):
                    extracted_text = alt
            if not extracted_text.strip():
                # Extra fallback: sometimes Azure may put text at choice level (rare)
                choice_level_text = choice.get('text') or choice.get('content')
                if isinstance(choice_level_text, str) and choice_level_text.strip():
                    extracted_text = choice_level_text.strip()
                if not extracted_text.strip():
                    # Provide richer diagnostics (Suggestion B)
                    msg_keys = list(msg.keys())
                    choice_keys = list(choice.keys())
                    finish = choice.get('finish_reason')
                    usage = data.get('usage') if isinstance(data, dict) else None
                    print(
                        f"[{debug_prefix}] Empty content debug: finish_reason={finish} attempts={attempt+1}/{max_retries} "
                        f"msg_keys={msg_keys} choice_keys={choice_keys} usage={usage} raw_message={msg} choice_obj={choice}"
                    )
                    err_detail = (
                        f"Empty completion content (finish_reason={finish} msg_keys={msg_keys} choice_keys={choice_keys})"
                    )
                    return None, err_detail, data, finish
            return extracted_text.strip(), None, data, choice.get('finish_reason')
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                delay = base_delay * (attempt + 1)
                print(f"[{debug_prefix}] Timeout; retrying in {delay}s")
                time.sleep(delay)
                continue
            return None, "Request timed out", None, None
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                delay = base_delay * (attempt + 1)
                print(f"[{debug_prefix}] Connection error; retrying in {delay}s")
                time.sleep(delay)
                continue
            return None, "Connection error", None, None
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if getattr(e, 'response', None) else 'Unknown'
            snippet = ''
            try:
                body = e.response.text if e.response is not None else ''
                snippet = (body[:300] + '...') if len(body) > 300 else body
            except Exception:
                pass
            return None, f"HTTP error {status}: {snippet}", None, None
        except Exception as ex:
            return None, f"Unexpected exception: {ex}", None, None
    return None, "Exceeded retries", None, None

# ---------------------------------------------------------------------------
# Normalization Utilities (Item 2)
# ---------------------------------------------------------------------------
_FENCE_RE = re.compile(r"```[a-zA-Z0-9]*\n|```", re.MULTILINE)

def strip_code_fences(text: str) -> str:
    if not text:
        return text
    return _FENCE_RE.sub("", text).strip()

def truncate_text(text: str, max_chars: int, suffix: str = "...TRUNCATED...") -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + suffix

def normalize_content(raw_text: str) -> str:
    """Normalize raw model content: strip code fences, collapse excessive blank lines and whitespace."""
    if not raw_text:
        return raw_text
    stripped = strip_code_fences(raw_text)
    # Collapse multiple blank lines
    collapsed = re.sub(r"\n{3,}", "\n\n", stripped)
    # Trim trailing spaces per line
    cleaned_lines = [ln.rstrip() for ln in collapsed.splitlines()]
    final = "\n".join(cleaned_lines).strip()
    return final

# ---------------------------------------------------------------------------
# ChatResult + run_chat wrapper (Item 3)
# ---------------------------------------------------------------------------
@dataclass
class ChatResult:
    content: Optional[str]
    finish_reason: Optional[str]
    error: Optional[str]
    raw: Optional[Dict[str, Any]]
    attempts: int
    escalated: bool
    metadata: Dict[str, Any]
    usage: Dict[str, int] | None = None

# ---------------------------------------------------------------------------
# Unified JSON Logging Hook (Item 8)
# ---------------------------------------------------------------------------
def _sha256_short(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def emit_chat_event(result: ChatResult, extra: Optional[Dict[str, Any]] = None) -> None:
    """Write a JSON line representing a chat invocation (if logging enabled).

    Controlled via env:
      AZURE_OPENAI_JSON_LOG=1 to enable.
      AZURE_OPENAI_JSON_LOG_PATH=custom path (default: ./logs/chat_events.jsonl)
    Content policy: do NOT store full content unless AZURE_OPENAI_LOG_FULL=1
    We store hashes + truncated preview by default.
    """
    if os.environ.get("AZURE_OPENAI_JSON_LOG", "0") != "1":
        return
    try:
        log_path = os.environ.get("AZURE_OPENAI_JSON_LOG_PATH", os.path.join("logs", "chat_events.jsonl"))
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        full_allowed = os.environ.get("AZURE_OPENAI_LOG_FULL", "0") == "1"
        content_preview = None
        content_hash = None
        if result.content:
            content_hash = _sha256_short(result.content)
            if full_allowed:
                content_preview = result.content
            else:
                content_preview = truncate_text(result.content, 240)
        payload = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "purpose": result.metadata.get("purpose"),
            "deployment": result.metadata.get("deployment"),
            "api_version": result.metadata.get("api_version"),
            "is_o_model": result.metadata.get("is_o_model"),
            "attempts": result.attempts,
            "escalated": result.escalated,
            "finish_reason": result.finish_reason,
            "error_code": result.metadata.get("error_code"),
            "error": result.error,
            "initial_max_tokens": result.metadata.get("initial_max_tokens"),
            "final_max_tokens": result.metadata.get("final_max_tokens"),
            "temperature": result.metadata.get("temperature"),
            "top_p": result.metadata.get("top_p"),
            "content_hash": content_hash,
            "content_preview": content_preview,
            "usage": result.usage or {},
        }
        if extra:
            payload["extra"] = extra
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as log_exc:
        print(f"[emit_chat_event] Logging failed: {log_exc}")

# ---------------------------------------------------------------------------
# Error Codes (Item 5)
# ---------------------------------------------------------------------------
class ErrorCodes:
    AUTH = "auth_error"
    RATE_LIMIT = "rate_limit"
    DEPLOYMENT_NOT_FOUND = "deployment_not_found"
    EMPTY = "empty_content"
    FILTERED = "content_filtered"
    TIMEOUT = "timeout"
    CONNECTION = "connection_error"
    HTTP = "http_error"
    GENERIC = "generic_error"

def classify_error(err: Optional[str]) -> Optional[str]:
    if not err:
        return None
    e = err.lower()
    if "auth" in e or "401" in e:
        return ErrorCodes.AUTH
    if "rate limit" in e or "429" in e:
        return ErrorCodes.RATE_LIMIT
    if "deployment not found" in e or "404" in e:
        return ErrorCodes.DEPLOYMENT_NOT_FOUND
    if "empty completion" in e or "empty content" in e:
        return ErrorCodes.EMPTY
    if "filtered" in e or "content policy" in e:
        return ErrorCodes.FILTERED
    if "timeout" in e:
        return ErrorCodes.TIMEOUT
    if "connection" in e:
        return ErrorCodes.CONNECTION
    if "http error" in e:
        return ErrorCodes.HTTP
    return ErrorCodes.GENERIC

# ---------------------------------------------------------------------------
# Token Escalation (Item 4)
# ---------------------------------------------------------------------------
def maybe_escalate_tokens(finish_reason: Optional[str], current_tokens: int, ceiling: int) -> Optional[int]:
    """If finish reason indicates truncation and we have headroom, escalate token budget.
    Strategy: increase by 50% up to ceiling (at least +50 tokens if small).
    """
    if finish_reason != "length":
        return None
    if current_tokens >= ceiling:
        return None
    increment = max(int(current_tokens * 0.5), 50)
    new_tokens = min(current_tokens + increment, ceiling)
    if new_tokens <= current_tokens:
        return None
    return new_tokens

def run_chat(
    *,
    system_prompt: str,
    user_prompt: str,
    purpose: str,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    allow_escalation: bool = False,
    escalation_ceiling: Optional[int] = None,
    adapt_temperature: bool = True,
    temp_increment: float | None = None,
    max_temperature: float | None = None,
    debug_prefix: Optional[str] = None,
    cfg: AzureOpenAIConfig | None = None,
) -> ChatResult:
    """High-level wrapper providing a stable contract for call sites.

    Responsibilities:
      - Load config & detect model type
      - Build messages & payload (with overrides)
      - Execute chat with retries
      - Normalize returned content
      - (Future) Token escalation hook
    """
    cfg = cfg or load_config()
    if not cfg:
        return ChatResult(content=None, finish_reason=None, error="Missing configuration", raw=None, attempts=0, escalated=False, metadata={"purpose": purpose})

    is_o = _is_o_model(cfg.deployment)
    initial_tokens = max_tokens
    if initial_tokens is None:
        # Mirror logic inside build_chat_request (updated default 1000)
        initial_tokens = get_env_int("AZURE_OPENAI_MAX_OUTPUT_TOKENS", 1000, min_value=50, max_value=4000)
    # Escalation ceiling default raised from 1200 -> 2000 to permit one or two larger expansions.
    ceiling = escalation_ceiling or get_env_int("AZURE_OPENAI_ESCALATION_CEILING", 2000, min_value=initial_tokens, max_value=4000)

    attempts = 0
    escalated = False
    current_tokens = initial_tokens
    dbg = debug_prefix or purpose.capitalize()

    content: Optional[str] = None
    error_msg: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None

    base_temp_env = float(os.environ.get("AZURE_OPENAI_TRANSLATE_BASE_TEMP", "0.1"))
    increment = temp_increment if temp_increment is not None else float(os.environ.get("AZURE_OPENAI_TEMP_INCREMENT", "0.05"))
    max_temp_cap = max_temperature if max_temperature is not None else float(os.environ.get("AZURE_OPENAI_TEMP_MAX", "0.6"))

    current_temperature = temperature if temperature is not None else base_temp_env

    for loop in range(2):  # at most one escalation cycle
        messages = build_messages(system_prompt, user_prompt, is_o_model=is_o)
        payload = build_chat_request(
            messages,
            is_o_model=is_o,
            max_tokens=current_tokens,
            temperature=current_temperature,
            top_p=top_p,
        )
        c, e, r, fr = chat_completion(cfg, payload, debug_prefix=dbg + ("-Escalated" if loop == 1 else ""))
        attempts += 1
        content, error_msg, raw, finish_reason = c, e, r, fr
        if error_msg:
            break  # no escalation on explicit API error
        if allow_escalation:
            new_tokens = maybe_escalate_tokens(finish_reason, current_tokens, ceiling)
            if new_tokens and not escalated:
                print(f"[run_chat] Escalating max_tokens {current_tokens} -> {new_tokens} (finish_reason=length)")
                current_tokens = new_tokens
                if adapt_temperature:
                    current_temperature = min(current_temperature + increment, max_temp_cap)
                escalated = True
                continue  # perform escalated retry
        break  # normal exit

    norm = normalize_content(content) if content and not error_msg else None

    usage = None
    if raw and isinstance(raw, dict):
        usage_raw = raw.get('usage') or {}
        if isinstance(usage_raw, dict):
            usage = {
                k: int(v) for k, v in usage_raw.items() if isinstance(v, (int, float))
            }

    return ChatResult(
        content=norm,
        finish_reason=finish_reason,
        error=error_msg,
        raw=raw,
        attempts=attempts,
        escalated=escalated,
        metadata={
            "purpose": purpose,
            "deployment": cfg.deployment,
            "api_version": cfg.api_version,
            "is_o_model": is_o,
            "initial_max_tokens": initial_tokens,
            "final_max_tokens": current_tokens,
            "temperature": current_temperature,
            "top_p": top_p,
            "error_code": classify_error(error_msg),
        },
        usage=usage,
    )

# ---------------------------------------------------------------------------
# Secret Masking (centralized)
# ---------------------------------------------------------------------------
_SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"Bearer\s+[A-Za-z0-9-_.]+"),
    re.compile(r"-----BEGIN [A-Z ]+-----[\s\S]+?-----END [A-Z ]+-----"),
    re.compile(r"(?i)api[_-]?key[:=]\s*[A-Za-z0-9-_]{10,}"),
]

def mask_secrets(text: str) -> str:
    if not text:
        return text
    masked = text
    for pat in _SECRET_PATTERNS:
        masked = pat.sub("[REDACTED]", masked)
    return masked

# ---------------------------------------------------------------------------
# Facade: OpenAIClient
# ---------------------------------------------------------------------------
class OpenAIClient:
    """Public facade providing stateful reuse of configuration & convenience methods.

    Example:
        client = OpenAIClient()
        res = client.chat(system_prompt, user_prompt, purpose="translate")
    """
    def __init__(self, cfg: AzureOpenAIConfig | None = None):
        self.cfg = cfg or load_config()
        if not self.cfg:
            raise RuntimeError("Azure OpenAI configuration missing (endpoint/key)")

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        purpose: str = "generic",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        allow_escalation: bool = True,
        escalation_ceiling: Optional[int] = None,
        adapt_temperature: bool = True,
        temp_increment: Optional[float] = None,
        max_temperature: Optional[float] = None,
        debug_prefix: Optional[str] = None,
        log_event: bool = False,
        extra_log: Optional[Dict[str, Any]] = None,
    ) -> ChatResult:
        result = run_chat(
            system_prompt=mask_secrets(system_prompt),
            user_prompt=mask_secrets(user_prompt),
            purpose=purpose,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            allow_escalation=allow_escalation,
            escalation_ceiling=escalation_ceiling,
            adapt_temperature=adapt_temperature,
            temp_increment=temp_increment,
            max_temperature=max_temperature,
            debug_prefix=debug_prefix,
            cfg=self.cfg,
        )
        if log_event:
            emit_chat_event(result, extra=extra_log)
        return result

    # Convenience wrappers
    def translate(self, prompt: str, question: str, **kwargs) -> ChatResult:
        return self.chat(system_prompt=prompt, user_prompt=f"Question: {question}\nReturn ONLY the KQL query.", purpose="translate", **kwargs)

    def explain(self, system_prompt: str, summary: str, **kwargs) -> ChatResult:
        return self.chat(system_prompt=system_prompt, user_prompt=summary, purpose="explain", **kwargs)

# ---------------------------------------------------------------------------
# Embeddings Helper (Azure + fallback)
# ---------------------------------------------------------------------------
def run_embeddings(texts: List[str], *, cfg: AzureOpenAIConfig | None = None, model: Optional[str] = None, timeout: int = 30) -> Tuple[Optional[List[List[float]]], Optional[str]]:
    """Obtain embedding vectors from Azure OpenAI for the provided list of texts.

    Returns (vectors, error). Each vector is L2-normalized. On any failure returns (None, error_message).

    Environment / selection:
      - Uses existing AzureOpenAIConfig (endpoint, deployment, api_version).
      - If EMBEDDING_DEPLOYMENT env var set, overrides deployment for embeddings only.
      - If model param provided, include it; otherwise rely on deployment name. Some previews require 'model'.
    """
    if not texts:
        return [], None
    cfg = cfg or load_config()
    if not cfg:
        return None, "Missing Azure OpenAI configuration"
    embedding_deployment = cfg.embedding_deployment

    # If the base chat deployment is an o-model family (o1/o4) and the user did NOT provide
    # an explicit embedding deployment, embeddings will fail (HTTP 400 OperationNotSupported).
    # Proactively surface a clear error instead of making the HTTP call.
    if embedding_deployment == cfg.deployment and _is_o_model(cfg.deployment):
        return None, (
            f"Embeddings not supported for o-model deployment '{cfg.deployment}'. "
            "Create a separate embedding deployment (e.g. text-embedding-3-small) and set AZURE_OPENAI_EMBED_DEPLOYMENT."
        )

    # Optional explicit embedding model override (Azure sometimes requires 'model' field for certain API versions)
    explicit_model = cfg.embedding_model or model
    embedding_api_version = cfg.embedding_api_version
    embeddings_base_endpoint = cfg.embedding_endpoint.rstrip('/')
    url = f"{embeddings_base_endpoint}/openai/deployments/{embedding_deployment}/embeddings?api-version={embedding_api_version}"
    headers = {"Content-Type": "application/json", "api-key": cfg.embedding_api_key}
    payload: Dict[str, Any] = {"input": texts}
    if explicit_model:
        payload["model"] = explicit_model
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
        if resp.status_code == 401:
            return None, "Authentication failed (401) for embeddings"
        if resp.status_code == 404:
            return None, f"Embeddings deployment not found (404): {embedding_deployment}"
        if resp.status_code == 429:
            return None, "Rate limited (429) for embeddings"
        if resp.status_code >= 400:
            snippet = resp.text[:300] if hasattr(resp, 'text') else ''
            return None, f"HTTP {resp.status_code}: {snippet}"
        data = resp.json()
        if 'error' in data:
            raw_err = data['error'].get('message', 'Unknown embeddings error')
            # Augment common OperationNotSupported with guidance
            if 'OperationNotSupported' in raw_err or 'does not work with the specified model' in raw_err:
                raw_err += (
                    " | Hint: Ensure AZURE_OPENAI_EMBED_DEPLOYMENT references a dedicated embedding model "
                    "(e.g. text-embedding-3-small, text-embedding-3-large, text-embedding-ada-002)."
                )
            return None, raw_err
        items = data.get('data') or []
        vectors: List[List[float]] = []
        for item in items:
            vec = item.get('embedding') or []
            if not isinstance(vec, list):
                continue
            norm = (sum(v*v for v in vec) ** 0.5) or 1.0
            vectors.append([v / norm for v in vec])
        if not vectors:
            return None, "No embedding vectors returned"
        return vectors, None
    except requests.exceptions.Timeout:
        return None, "Embeddings request timed out"
    except Exception as e:
        return None, f"Embeddings unexpected error: {e}"

def create_embeddings(texts: List[str]) -> Optional[List[List[float]]]:
    """Return Azure embeddings for provided texts (Azure-only).

    If Azure configuration or embedding retrieval fails, returns None.
    Public OpenAI fallback removed by design to ensure single provider semantics.
    """
    azure_cfg = load_config()
    if not azure_cfg:
        return None
    vectors, err = run_embeddings(texts, cfg=azure_cfg)
    if vectors is not None:
        print(f"[embeddings] provider=azure deployment={azure_cfg.embedding_deployment} count={len(vectors)}")
        return vectors
    print(f"[embeddings] azure_failed error='{err}' (Azure-only, no fallback)")
    return None
