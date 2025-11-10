# Prompt Integration Guidelines for AKS & Container Log Intelligence

This guide describes how to evolve system and user prompts so agents leverage the newly added ontology, KQL helper snippets, and domain knowledge artifacts:

- `docs/containers_capsule/container_ontology.md`
- `docs/containers_capsule/kql_functions_containerlogs.kql`
- `docs/containers_capsule/prompt_template_containerlogs.txt`

It proposes a *layered prompt architecture* that keeps base instructions stable, injects only minimally necessary structured knowledge at runtime, and reduces prompt token waste.

---
## 1. Prompt Layering Strategy

| Layer | Purpose | Source | Update Cadence |
|-------|---------|--------|----------------|
| L0 Core System | Immutable safety + role + output contract | Hand-authored | Rare |
| L1 Domain Capsule | Summarized ontology & entity relationships | Generated from `containers_capsule/container_ontology.md` (compressed) | Regenerate when ontology changes |
| L2 Tooling & Functions | Available reusable KQL snippets & their invocation semantics | `containers_capsule/kql_functions_containerlogs.kql` (enumerated names only) | When functions file changes |
| L3 Dynamic Retrieval | Narrow, query-specific facts (labels, example queries) | Lightweight RAG over docs | Per request |
| L4 User Query | Original or clarified user request | User | Per request |
| L5 Chain-of-Thought Guardrail | “Think step-wise but return only final answer/KQL” | Static instruction | Stable |
| L6 Output Format Directive | KQL-only vs Explanation + KQL | System + contextual preference | Stable |

---
## 2. Core System Prompt (L0)
```
You are an autonomous analytical assistant specialized in Azure Kubernetes Service (AKS) and Container Observability.
Objectives:
- Translate natural language into safe, efficient KQL.
- Provide concise operational or reliability insights grounded in cluster telemetry.
Rules:
1. NEVER fabricate table or column names.
2. If required data is absent, explicitly state limitation and suggest enabling relevant diagnostic category.
3. Optimize queries for least cost (filter time early, project minimally, avoid unnecessary parse_json).
4. Default timeframe: last 1 hour when unspecified (communicate assumption).
5. ALWAYS confirm risky wide scans (>7d across all namespaces) with a warning.
6. Use workload-level aggregation (labels) unless user explicitly says per-pod.
7. Provide both counts and rates for error-related comparisons.
8. Redact tokens, secrets, credentials if they appear in logs.
9. Return KQL only unless user explicitly requests explanation.
10. If user asks "why" provide brief reasoning then KQL.
```

---
## 3. Domain Capsule (L1) – Summarized Knowledge Snippet
*Generate automatically (e.g., nightly) from ontology; keep < 800 tokens.*

Example compressed snippet:
```
Entities: Cluster > Node > Pod > Container > LogEntry (with Severity, StructuredPayload, optional StackTrace). Labels derive WorkloadName preferring app.kubernetes.io/name > app > service > PodName. Error classification: LogLevel in (CRITICAL, ERROR) OR LogSource=='stderr'. Performance: extract latency via regex 'latency[=:]([0-9]+)ms'. Crash loops correlate RestartCount (KubePodInventory) + recent error spikes. Table focus: ContainerLogV2 core cols (Computer, ContainerId, ContainerName, PodName, PodNamespace, LogMessage dynamic, LogSource, TimeGenerated, KubernetesMetadata dynamic, LogLevel).
```

Store current snippet in a small file: `docs/domain_capsule_containerlogs.txt` (optional) and splice it at runtime.

---
## 4. Tooling & Functions Declaration (L2)
*Do NOT paste full bodies into the prompt.* List function names + intent:
```
Available Virtual Functions (logical patterns):
- ProjectStandard(): normalize labels, workload name, error flags.
- ContainerErrorRate(lookback): errors & rate per workload.
- HighLatencyLogs(lookback, threshold).
- StackTraceLines(lookback).
- StructuredStatus(lookback, statusCode).
- NoisyContainers(lookback, topN).
- CrashLoopCorrelation(lookback): joins restarts & errors.
```
Instruction: “If user intent maps 1:1 to a function, invoke pattern; else compose base fragments.”

---
## 5. Dynamic Retrieval Layer (L3)
At runtime:
1. Extract intent keywords (e.g., error rate, crash loop, latency > 400ms, status=500).
2. Select relevant functions by keyword match (error -> ContainerErrorRate; crash -> CrashLoopCorrelation; latency -> HighLatencyLogs).
3. Pull only *relevant lines* from `containers_capsule/container_ontology.md` (section describing entity or pattern) if disambiguation needed.

---
## 6. User Query Layer (L4)
Optionally rewrite for clarity (NOT altering semantic intent):
```
Original: "why payment svc so many errs?"
Clarified: "Explain elevated error rate for payments workload last 2h and show top error-producing containers."
```
Add note if timeframe assumed: “Assuming last 1h (user unspecified).”

---
## 6. Chain-of-Thought Guardrail (L5)
Internal reasoning instruction (NOT shown to user output):
```
Think step-by-step silently; produce final answer in required format only. Do not expose internal reasoning.
```

---
## 7. Output Format Directive (L6)
Decision rules:
| Situation | Output |
|-----------|--------|
| Pure data request | KQL only |
| "Explain", "Why", "Describe" present | Short explanation paragraph + KQL block |
| Ambiguous / missing timeframe | State assumption + KQL |
| Overbroad query risk | Warning + fallback narrower KQL suggestion |

Add standard postamble for multi-query responses:
```
-- Query 1: Summary by workload
-- Query 2: Detailed latency outliers
```

---
## 8. Few-Shot Prompt Augmentation (Optional)
Include 2–3 minimal exemplars to anchor style:
```
Q: Show error rate by workload last 30m.
A (KQL): <single query>
Q: Why are pods stuck pending in finance namespace?
A: Short cause hypothesis (uses KubePodInventory) + KQL.
```
Ensure total tokens remain under system threshold.

---
## 9. Safety & Data Minimization Additions
Add to system layer:
```
If logs appear to contain secrets (patterns: 'AKIA', 'Bearer ', '-----BEGIN'), mask value with '[REDACTED]'.
```
Add to domain capsule:
```
Do not re-emit full stack traces longer than 40 lines; truncate with '[TRUNCATED]'.
```

---
## 10. Integrating with Existing Code
Where to store new prompts:
- System template: `prompts/system_base.txt`
- Domain capsule auto-gen: `prompts/domain_capsule_containerlogs.txt`
- Few-shots: `prompts/fewshots_containerlogs.txt`
- Assembly logic (Python): add a `prompt_builder.py` that:
  1. Reads base system
  2. Conditionally appends capsule
  3. Injects function list (names only)
  4. Adds dynamic retrieval context
  5. Merges clarified user question & output directive

Pseudo-interface:
```python
def build_prompt(user_query: str, intent_meta: dict) -> str:
    system = load('prompts/system_base.txt')
    capsule = load('prompts/domain_capsule_containerlogs.txt')
    functions = summarize_functions(['kql_functions_containerlogs.kql'])
    retrieval = retrieve_snippets(user_query)
    clarified = clarify(user_query)
    directive = decide_output_mode(clarified, intent_meta)
    return f"{system}\n\n{capsule}\n\nFunctions:\n{functions}\n\nContext Addendum:\n{retrieval}\n\nUser Request:\n{clarified}\n\n{directive}"
```
---
## 11. Versioning & Drift Control
- Maintain `PROMPT_SCHEMA_VERSION` constant; increment if structure changes.
- Include version at top of system prompt: `# PromptSchemaVersion:2`.
- Log prompt hash with each AI invocation for reproducibility.

---
## 12. Metrics for Prompt Effectiveness
Track (store per invocation):
- Token count (system vs user portion)
- Query success (no syntax error / execution ok)
- Average response latency
- Error detection precision (false positives/negatives for IsError)
- User follow-up rate (proxy for clarity)

Use these to drive iterative trimming of low-value text.
