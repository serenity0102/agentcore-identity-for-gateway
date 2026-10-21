# tests/results/
Saved outputs of the Gateway tool RBAC test runs. These are evidence for `RUNBOOK-cognito-idc.md` (Part 4 · OBO → Per-user enforcement downstream, Gateway tool RBAC); regenerate them by re-running the tests.
- `rbac_baseline.json`, `rbac_log_only.json`, `rbac_enforce.json`: `tests/rbac_tests.py <phase>`.
- `rbac_changes.json`: `tests/rbac_change_tests.py`, the IdC-only change tests 7 and 8.
- `rbac_log_only_decisions.json`: gateway log entries with the Policy decision in LOG_ONLY mode.
- `rbac_initialize_probe.txt`: `initialize` and `tools/list` under ENFORCE without explicit permits.
- `rbac_regression_obo.txt`, `rbac_regression_oauth.txt`: regression runs of `validate_matrix.py` and `oauth_tests.py`.
No tokens or passwords are stored.
- `mall_log_only.json`, `mall_enforce.json`, `mall_change.json`: Part 4 (customer version) test runs.
