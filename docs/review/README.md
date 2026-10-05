# docs/review/
Evidence pack produced with the `aws-deploy-evidence` skill (~/.claude/skills/aws-deploy-evidence).
- `review.pdf` / `review.html` / `REVIEW.md`: open one of these to review. They cover every deployed resource in deployment order (infra/01 → 13), with a console screenshot (exact URL + capture time), read-only verification commands with expected and actual output, and PASS/FAIL.
- `shots.tsv`: the ordered list of console pages (name, URL, caption, actions). `review.json`: steps, resources and verify checks. `findings.md`: findings.
- `img/`: screenshots plus `manifest.tsv`, which holds the URL and timestamp at capture. `img/parts/`: tall pages sliced for print.
- Rebuild (read-only):
  - `python3 ~/.claude/skills/aws-deploy-evidence/scripts/capture.py docs/review/shots.tsv docs/review/img`, which needs Chrome logged in to the console;
  - then `python3 ~/.claude/skills/aws-deploy-evidence/scripts/build_review.py docs/review/review.json`.
