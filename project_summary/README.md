# Project Summary Index

This directory decomposes the overall project summary into focused sections for easier maintenance and review.

## Index
1. `01_high_level_architecture.mmd` – Mermaid high-level architecture diagram
2. `02_component_responsibilities.md` – Table of core components and purposes
3. `03_data_flow_ascii.md` – Plain-text data & control flow
4. `04_sequence_diagram.mmd` – Mermaid sequence diagram of a request lifecycle
5. `05_extensibility_points.md` – Places to extend or customize
6. `06_azure_dependencies.md` – Azure services, env vars, auth modes
7. `PROJECT_SUMMARY.md` – Original consolidated summary (legacy aggregate)

## Viewing Mermaid Diagrams
GitHub renders `.mmd` inside fenced `mermaid` blocks only when embedded in Markdown. If your client doesn't show them automatically:
- Use VS Code + Mermaid preview extension
- Or convert with: `npx @mermaid-js/mermaid-cli -i 01_high_level_architecture.mmd -o arch.svg`

## Maintenance Guidelines
- Update diagrams when adding interfaces or changing agent workflow.
- Keep component responsibility table synchronized with code moves/renames.
- Prefer adding new focused files over bloating a single document.
