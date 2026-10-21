# data/
Published assets that `RUNBOOK-cognito-idc.md` (and the scripts) link to. `docs/` is local only, so anything the repo references lives here.
- `architecture*.svg`: architecture diagrams (OBO, 2LO, 3LO, Quick → mall gateway, tool RBAC demo and customer versions). Their `.tsx` sources stay in the local `docs/`.
- `flow.html` (built by `python3 data/build_flow.py` from `flow_template.html` + the three SVGs) and `flow-rbac.html` (built from `flow-rbac.config.mjs` with the diagram skill): animated token-flow pages.
- `data-views.md` / `.html`: per-persona Redshift output, written by `tests/render_data_views.py`.
- `quick-mcp-connector.md`: how to connect Amazon Quick to the mall gateway.
- `img/`: AWS console screenshots referenced from the runbook (`img/console/manifest.tsv` records the URL at capture time).
