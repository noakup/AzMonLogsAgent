# Extensibility Points

| Area | How to Extend | Notes |
|------|---------------|-------|
| New Interface | Add module calling `KQLAgent` | Reuse agent contract to avoid duplication. |
| Additional Models | Plug into `nl_to_kql.py` abstraction | Provide adapter for prompt + response normalization. |
| Schema Expansion | Drop new schema files under `NGSchema/` | Auto-discovered if scanning logic present. |
| Caching Layer | Wrap translation or query calls | Introduce TTL and schema versioning. |
| Observability | Instrument `monitor_client.py` | Add logging, metrics, trace spans. |
| Validation | Pre-execution KQL static checks | Could add lint step before Azure Monitor call. |
| Security | Add query allow/deny rules | Insert before execution in agent. |
