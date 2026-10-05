# tests/
End-to-end checks against the deployed runtime. Run from this folder via `../infra/run.sh`.
- `validate_matrix.py`: 16 allow/deny cases across 4 IdC personas. A DENY only passes on a Redshift `permission denied` error.
- `negative_tests.py`: no token, forged token, JWT replay in a new session, LLM prompt injection.
- `network_tests.sh`: source IPs seen by Redshift, SG revoke/restore proof, and an admin token-exchange attempt.
- `oauth_tests.py`: Part 2, 2LO/3LO against the separate OAuth runtime (automated consent with agent-browser, a local :8765 callback, and throwaway admin-created users). Results in `results-oauth.txt`.
- `tokens.py` / `invoke.py`: Cognito sign-in and HTTPS invocation with a bearer token.
- `results-*.txt`: saved outputs. `.users.env`: local test passwords (chmod 600, gitignored).
