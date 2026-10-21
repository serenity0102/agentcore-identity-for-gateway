# tests/
End-to-end checks against the deployed runtime. Run from this folder via `../infra/run.sh`.
- `validate_matrix.py`: 16 allow/deny cases across 4 IdC personas. A DENY only passes on a Redshift `permission denied` error.
- `negative_tests.py`: no token, forged token, JWT replay in a new session, LLM prompt injection.
- `network_tests.sh`: source IPs seen by Redshift, SG revoke/restore proof, and an admin token-exchange attempt.
- `oauth_tests.py`: Part 2, 2LO/3LO against the separate OAuth runtime (automated consent with agent-browser, a local :8765 callback, and throwaway admin-created users). Results in `results-oauth.txt`.
- `rbac_tests.py <baseline|log_only|enforce>` and `rbac_change_tests.py`: Part 3, per-user tool RBAC on the RBAC gateway (Cedar on an Entra-style `roles` claim from IdC). Results in `results/`.
- `tokens.py` / `invoke.py`: Cognito sign-in (ID or access token) and HTTPS invocation with a bearer token.
- `results-*.txt`: saved outputs. `.users.env`: local test passwords (chmod 600, gitignored).
- `mall_rbac_tests.py <log_only|enforce|change>`: Part 4, the customer version. Uses tokens for the Quick app client (secret in gitignored `.quick-client.env`) against the mall Gateway. Results in `results/mall_*.json`.
