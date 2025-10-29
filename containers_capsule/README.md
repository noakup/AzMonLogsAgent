# Containers Capsule

This capsule provides domain-specific prompt scaffolding, ontology, and reusable KQL snippets for Azure Monitor Container Logs analytics.

## Contents
- `container_ontology.md` - Concepts, entities, derived fields, sample queries.
- `kql_functions_containerlogs.kql` - Reusable helper functions.
- `prompt_guidelines.md` - Authoring guidance for NL intents.
- `prompt_template_containerlogs.txt` - Base template injected before examples.
- `diagram_container_ontology.mmd` - Mermaid diagram of entity relationships.
- `kql_examples/container_logs_kql_examples.md` - Few-shot style NL→KQL examples (replaces deprecated `fewshots_containerlogs.txt`).

## Relocation Note
Relocated from `docs/containers_capsule/` to top-level `containers_capsule/` for parity with `app_insights_capsule/` and future domain modularity.

Update code references from:
```
docs/containers_capsule/<file>
```
to:
```
containers_capsule/<file>
```

## TODO
- Adjust all imports/path reads in code (`prompt_builder.py`, `nl_to_kql.py`). (DONE)
- Remove or stub legacy directory. (DONE)
- Add tests for few-shot example selection referencing new path. (PENDING)
- Clean up any residual references to deprecated `fewshots_containerlogs.txt`. (IN-PROGRESS)
