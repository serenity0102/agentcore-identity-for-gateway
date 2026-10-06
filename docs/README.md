# docs/
Shareable artifacts for this test.
- `architecture.svg`: architecture diagram (official AWS icons). Source: `architecture.tsx`, a scene for the `aws-architecture-diagram-svg` skill (copy it into the skill's `scenes/` and run `npm run render`).
- `architecture-2lo.svg` (source `architecture-2lo.tsx`): Part 2 2LO diagram (client credentials → Gateway → svc_reporting) with its token-code panel.
- `architecture-3lo.svg` (source `architecture-3lo.tsx`): Part 2 3LO diagram (consent → AgentCore callback → session binding → Token Vault → userInfo) with its token-code panel.
- `_codepanel.ts`: helper that draws the "Key token code" panel inside the diagram scenes.
- `email-draft.html` → `email-draft.pdf`: email draft for colleagues covering architecture, setup, test steps and results. To regenerate the PDF, print the HTML with headless Chrome (`--print-to-pdf`).
- `flow.html`: **animated** token-flow walkthrough (tabs OBO / 2LO / 3LO; play, step, speed). It shows where the user logs in (LOGIN markers), how the JWT, IdC, M2M and vault tokens move, and each validation point. It is self-contained: open it in a browser, or use `flow.html#3lo` to start on a tab and `?autoplay=1` to auto-play. Built from `flow_template.html` and the two SVGs by `python3 docs/build_flow.py`. Email clients and PDFs cannot play it; the email keeps the static SVGs.
