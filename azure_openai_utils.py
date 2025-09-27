"""Shared Azure OpenAI helper utilities to centralize configuration, version selection,
payload construction, and URL building for both translation and explanation paths.
"""
from __future__ import annotations
import os
from typing import Dict, Tuple, Any, List, Optional
import json
import time
import requests

try:  # Optional dependency; don't fail if missing
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

DEFAULT_STANDARD_API_VERSION = "2024-09-01-preview"
DEFAULT_O_MODELS_API_VERSION = "2024-12-01-preview"

class AzureOpenAIConfig:
    def __init__(self, endpoint: str, api_key: str, deployment: str, api_version: str, is_override: bool):
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment = deployment
        self.api_version = api_version
        self.is_override = is_override

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

    if not endpoint or not api_key:
        print("[debug:] Missing endpoint or API key in environment variables.")
        return None

    if not endpoint.startswith("http"):
        endpoint = f"https://{endpoint}"
    endpoint = endpoint.rstrip('/')

    if api_version_override:
        api_version = api_version_override
        is_override = True
        print(f"[debug:] Using overridden API version: {api_version}")
    else:
        # Adaptive selection
        if _is_o_model(deployment):
            api_version = DEFAULT_O_MODELS_API_VERSION
        else:
            api_version = DEFAULT_STANDARD_API_VERSION
        is_override = False
        print(f"[debug:] Selected API version: {api_version} (o-model={_is_o_model(deployment)})")

    return AzureOpenAIConfig(endpoint, api_key, deployment, api_version, is_override)

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

def build_chat_request(messages: List[Dict[str, str]], *, is_o_model: bool) -> Dict[str, Any]:
    max_output_tokens = get_env_int("AZURE_OPENAI_MAX_OUTPUT_TOKENS", 500, min_value=50, max_value=4000)
    if is_o_model:
        return build_payload(messages, is_o_model=True, max_output_tokens=max_output_tokens)
    
    base_temperature = float(os.environ.get("AZURE_OPENAI_TRANSLATE_BASE_TEMP", "0.1"))
    return build_payload(messages, is_o_model=False, max_output_tokens=max_output_tokens, temperature=base_temperature, top_p=0.9)

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
                    # Provide rich debug context
                    print(f"[{debug_prefix}] Empty content debug: msg_keys={list(msg.keys())}; choice_keys={list(choice.keys())}; raw_message={msg}; choice={choice}")
                    return None, "Empty completion content", data, choice.get('finish_reason')
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
