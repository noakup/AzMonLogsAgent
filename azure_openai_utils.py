"""Shared Azure OpenAI helper utilities to centralize configuration, version selection,
payload construction, and URL building for both translation and explanation paths.
"""
from __future__ import annotations
import os
from typing import Dict, Tuple, Any

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
        return f"{self.base_url()}/chat/completions?api-version={self.api_version}"

def load_config() -> AzureOpenAIConfig | None:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
    api_version_override = os.environ.get("AZURE_OPENAI_API_VERSION")

    if not endpoint or not api_key:
        return None

    if not endpoint.startswith("http"):
        endpoint = f"https://{endpoint}"
    endpoint = endpoint.rstrip('/')

    if api_version_override:
        api_version = api_version_override
        is_override = True
    else:
        # Adaptive selection
        if _is_o_model(deployment):
            api_version = DEFAULT_O_MODELS_API_VERSION
        else:
            api_version = DEFAULT_STANDARD_API_VERSION
        is_override = False

    return AzureOpenAIConfig(endpoint, api_key, deployment, api_version, is_override)

def _is_o_model(deployment: str) -> bool:
    d = deployment.lower()
    return ("o1" in d) or ("o4" in d)

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
