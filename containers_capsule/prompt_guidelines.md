# Container Logs Prompt Authoring Guidelines
(Relocated from `docs/containers_capsule/prompt_guidelines.md`)

These guidelines help shape NL → KQL translation for container log analytics.

## Tone & Structure
- Start with explicit task intent ("Find error rate per workload").
- Specify timeframe if non-default (default assumed: last 1h).
- Mention key severity concepts: error, latency, volume, restarts.
- Prefer nouns matching ontology: workload, pod, namespace, container.

## Recommended Clarifications
| Ask | Why |
|-----|-----|
| Time range | Narrow compute scope |
| Workload namespace | Reduce cross-noise |
| Severity criteria | Distinguish errors from info |
| Output columns | Avoid over-wide tables |
| Sort order | Ensure result interpretability |

## Query Pattern Blocks
1. Workload name derivation (labels fallback).
2. Error classification (stderr or level).
3. Structured JSON inspection when relevant.
4. Latency extraction with regex.
5. Aggregation with `summarize` + optional `bin(TimeGenerated, 5m)`.

## Anti-Patterns
- Unbounded time ranges ("all logs ever").
- Mixing container and host metrics in one query without join logic.
- Unfiltered free-text search with broad `has` terms.
- Large projection of all dynamic JSON properties.

## Heuristic Prompts Examples
| Raw Intent | Improved Prompt |
|------------|-----------------|
| show errors | "List top 20 workloads by error rate (stderr or level=error) last 2h" |
| high latency | "Find container log entries with latency >500ms in namespace 'payments' last 1h" |
| stack traces | "Summarize exception frequency per container (Exception or Traceback) last 24h" |
| crash loops | "Correlate pod restart counts with recent error volume last 1h" |

## Domain Keywords (Signal Strength)
error, stderr, crashloop, restart, latency, ms, namespace, workload, container, pod, exception, traceback, stack, image, status code, noisy

## Output Directives
- Present rates as percentages with 2 decimals.
- Keep table rows <= 50 unless user asks for more.
- Be explicit about derived fields.

## Extensibility Notes
Add future recipes for resource saturation, structured log field cardinality, anomaly scoring.

---
Relocated capsule asset.
