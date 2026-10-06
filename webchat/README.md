# webchat/
Local browser UI for the OBO data agent: Cognito managed login (code + PKCE) -> chat -> AgentCore Runtime with the user's ID token.
Run `infra/run.sh agent/.venv/bin/python webchat/app.py`, open http://localhost:8080, sign in as wei/zhang/chen/ds1 (passwords in `tests/.users.env`).
Binds 127.0.0.1 only; tokens stay server-side in memory. Requires `infra/13-web-login-client.py` (adds the localhost callback to the OBO client).

## 2LO / 3LO GUI (`oauth_app.py`, port 8081)
`infra/run.sh agent/.venv/bin/python webchat/oauth_app.py`, then open http://localhost:8081. It uses the separate OAuth runtime `rsidc_oauth_agent`.
- **2LO panel**: the agent's own M2M token → AgentCore Gateway → Lambda → Redshift as `svc_reporting`. It shows the token claims (no user) and the rows, which are the same for every user.
- **3LO panel**: login 2 (consent at Cognito) → AgentCore callback → `/3lo/callback` → `CompleteResourceTokenAuth` (session binding, using the operator's AWS credentials) → Token Vault → `userInfo`. Options: force re-consent; `prompt=login` (observed to store no token).
- Requires the 8081 callback on the Cognito client (`infra/13-web-login-client.py`) and `http://localhost:8081/3lo/callback` on the OAuth workload identity (`infra/12-deploy-oauth-runtime.sh`).

## Deployed on AWS (`infra/14-deploy-webchat.sh`)
Both apps run unchanged as Lambda Function URLs (HTTPS, because Cognito only allows http callbacks for localhost). `lambda_adapter.py` replays each Function URL event into the app's `BaseHTTPRequestHandler`.
- **Access:** only source IPs in `ALLOWED_IPS` are served (default: the operator IPv4s as /32 plus the current IPv6 /64, since the URL is dual-stack). Everything else gets a 403. Re-run the script after your IP changes, or set `WEB_ALLOWED_IPS`.
- **Sessions** are kept in memory, so each function has reserved concurrency 1. If the environment is recycled, sign in again. A request made while another is still running gets HTTP 429.
- The OAuth GUI's `CompleteResourceTokenAuth` uses the function role `rsidc-webchat-role`, not the operator's credentials.
