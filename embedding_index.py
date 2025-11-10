"""Persistent per-domain embedding index.

Builds and caches embeddings for example questions so runtime selection only embeds
incoming user question. Avoids re-embedding a large example corpus each request.

Env Vars:
  EMBED_INDEX_DIR            Directory for index files (default: ./embedding_index)
  REQUIRE_EMBEDDINGS         If '1', failure to build/load embeddings raises RuntimeError
  EMBED_INDEX_FORCE_REBUILD  If '1', always rebuild indexes on next load

Index JSON schema (version 1):
{
  "schema_version": 1,
  "domain": "containers",
  "created_at": "2025-11-06T12:34:56Z",
  "embedding_model": "text-embedding-3-small",
  "embedding_deployment": "text-embedding-3-small",
  "vector_dim": 1536,
  "examples_hash": "<sha256-short>",
  "examples": [
     {"id":0,"question":"..","kql":"..","question_hash":"..","vector":[0.01,...]}
  ]
}

Public API:
  load_or_build_domain_index(domain: str, examples: List[Dict[str,str]]) -> Dict
  select_with_index(nl_question: str, examples: List[Dict[str,str]], domain: str, top_k: int=3) -> List[Dict[str,str]]

This module is intentionally lightweight; concurrency concerns handled by atomic temp file rename.
"""
from __future__ import annotations
import os
import json
import time
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

from azure_openai_utils import create_embeddings, load_config  # type: ignore

SCHEMA_VERSION = 1

def _index_dir() -> str:
    d = os.environ.get("EMBED_INDEX_DIR", "embedding_index")
    os.makedirs(d, exist_ok=True)
    return d

def _index_path(domain: str) -> str:
    safe = domain.replace("/", "_")
    return os.path.join(_index_dir(), f"domain_{safe}_embedding_index.json")

# --------------------- Hash & Dirty Detection --------------------- #

def _examples_hash(examples: List[Dict[str,str]]) -> str:
    h = hashlib.sha256()
    for ex in examples:
        q = ex.get("question", "").strip()
        k = ex.get("kql", "").strip()
        h.update(q.encode("utf-8"))
        h.update(b"||")
        h.update(k.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()[:32]

# --------------------- Index Build --------------------- #

def build_domain_index(domain: str, public_shots: List[Dict[str,str]]) -> Dict:
    questions = [shot.get("question", "") for shot in public_shots]
    print(f"[embed-index] building domain={domain}")
    if not questions:
        return {
            "schema_version": SCHEMA_VERSION,
            "domain": domain,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "embedding_model": None,
            "embedding_deployment": None,
            "vector_dim": 0,
            "examples_hash": _examples_hash(public_shots),
            "examples": []
        }
    cfg = load_config()
    vectors = create_embeddings(questions)
    if vectors is None or not vectors:
        raise RuntimeError("Embeddings required but unavailable for index build.")
    dim = len(vectors[0]) if vectors and vectors[0] else 0
    examples_hash = _examples_hash(public_shots)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "domain": domain,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "embedding_model": cfg.embedding_model,
        "embedding_deployment": cfg.embedding_deployment,
        "vector_dim": dim,
        "examples_hash": examples_hash,
        "examples": []
    }
    for i, ex in enumerate(public_shots):
        payload["examples"].append({
            "id": i,
            "question": ex.get("question", ""),
            "kql": ex.get("kql", ""),
            "question_hash": hashlib.sha256(ex.get("question", "").encode("utf-8")).hexdigest()[:16],
            "vector": vectors[i] if i < len(vectors) else []
        })
    tmp_path = _index_path(domain) + ".tmp"
    final_path = _index_path(domain)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    os.replace(tmp_path, final_path)
    print(f"[embed-index] built domain={domain} examples={len(public_shots)} dim={dim} path={final_path}")
    return payload

# --------------------- Load or Build --------------------- #

def load_or_build_domain_index(domain: str, public_shots: List[Dict[str,str]]) -> Dict:
    path = _index_path(domain)
    force = os.environ.get("EMBED_INDEX_FORCE_REBUILD", "0") == "1"
    current_hash = _examples_hash(public_shots)
    if force:
        print(f"[embed-index] force rebuild domain={domain}")
        return build_domain_index(domain, public_shots)
    if not os.path.exists(path):
        return build_domain_index(domain, public_shots)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[embed-index] corrupt or unreadable index; rebuilding domain={domain} err={e}")
        return build_domain_index(domain, public_shots)
    if data.get("schema_version") != SCHEMA_VERSION:
        print(f"[embed-index] schema_version mismatch; rebuilding domain={domain}")
        return build_domain_index(domain, public_shots)
    if data.get("examples_hash") != current_hash:
        print(f"[embed-index] examples changed; rebuilding domain={domain}")
        return build_domain_index(domain, public_shots)
    # Basic sanity
    if not isinstance(data.get("examples"), list):
        print(f"[embed-index] malformed examples list; rebuilding domain={domain}")
        return build_domain_index(domain, public_shots)
    print(f"[embed-index] loaded domain={domain} examples={len(data['examples'])} dim={data.get('vector_dim')} path={path}")
    return data

# --------------------- Selection Using Index --------------------- #

def _tokenize(text: str) -> List[str]:
    import re
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and len(t) > 1]

def _heuristic_score(q_tokens: set, ex_question: str) -> int:
    ex_tokens = set(_tokenize(ex_question))
    score = 0
    if ex_question.lower() in " ".join(q_tokens) or any(ex_question.lower() in t for t in q_tokens):
        score += 10
    overlap = q_tokens.intersection(ex_tokens)
    score += len(overlap)
    if ("workload" in ex_tokens and "workload" in q_tokens) or ("latency" in ex_tokens and "latency" in q_tokens):
        score += 2
    if ("pod" in ex_tokens or "pods" in ex_tokens) and ("pod" in q_tokens or "pods" in q_tokens):
        score += 2
    return score

def select_with_index(nl_question: str, examples: List[Dict[str,str]], domain: str, top_k: int = 3) -> List[Dict[str,str]]:
    idx = load_or_build_domain_index(domain, examples)
    ex_list = idx.get("examples", [])
    if not ex_list:
        return []
    # Embed only the question
    q_vecs = create_embeddings([nl_question])
    if q_vecs is None or not q_vecs:
        if os.environ.get("REQUIRE_EMBEDDINGS", "0") == "1":
            raise RuntimeError("Embeddings required but unavailable for query embedding.")
        print("[embed-index] fallback heuristic only (no query vector)")
        q_tokens = set(_tokenize(nl_question))
        scored = [( _heuristic_score(q_tokens, ex["question"]), ex) for ex in ex_list]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for s, ex in scored[:top_k]]
    q_vec = q_vecs[0]
    # Build hybrid score like original: 0.55 heuristic + 0.45 cosine
    q_tokens = set(_tokenize(nl_question))
    max_h = 0
    records: List[Tuple[float, Dict[str,str]]] = []
    for ex in ex_list:
        h_score = _heuristic_score(q_tokens, ex.get("question", ""))
        if h_score > max_h:
            max_h = h_score
    for ex in ex_list:
        h_score = _heuristic_score(q_tokens, ex.get("question", ""))
        h_norm = (h_score / max_h) if max_h > 0 else 0.0
        vec = ex.get("vector", [])
        cosine = sum(a*b for a,b in zip(q_vec, vec)) if vec else 0.0
        final = 0.55 * h_norm + 0.45 * cosine
        records.append((final, ex))
    records.sort(key=lambda x: x[0], reverse=True)
    top = [ex for s, ex in records if s > 0][:top_k]
    if not top:
        top = [ex for s, ex in records[:top_k]]
    print(f"[embed-index] selection domain={domain} top_scores={[round(s,4) for s,_ in records[:3]]}")
    # Convert back to original example dict shape {question,kql}
    return [{"question": ex.get("question",""), "kql": ex.get("kql","" )} for ex in top]

__all__ = [
    "load_or_build_domain_index",
    "select_with_index",
    "build_domain_index",
]
