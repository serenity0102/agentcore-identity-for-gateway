# webchat/
Local browser UI for the OBO data agent: Cognito managed login (code + PKCE) -> chat -> AgentCore Runtime with the user's ID token.
Run `infra/run.sh agent_obo/.venv/bin/python webchat/app.py`, open http://localhost:8080, sign in as wei/zhang/chen/ds1 (passwords in `tests/.users.env`).
Binds 127.0.0.1 only; tokens stay server-side in memory. Requires `infra/13-web-login-client.py` (adds the localhost callback to the OBO client).

## 2LO / 3LO GUI (`oauth_app.py`, port 8081)
`infra/run.sh agent_obo/.venv/bin/python webchat/oauth_app.py`, then open http://localhost:8081. It uses the separate OAuth runtime `rsidc_oauth_agent`.
- **2LO panel**: the agent's own M2M token → AgentCore Gateway → Lambda → Redshift as `svc_reporting`. It shows the token claims (no user) and the rows, which are the same for every user.
- **3LO panel**: login 2 (consent at Cognito) → AgentCore callback → `/3lo/callback` → `CompleteResourceTokenAuth` (session binding, using the operator's AWS credentials) → Token Vault → `userInfo`. Options: force re-consent; `prompt=login` (observed to store no token).
- Requires the 8081 callback on the Cognito client (`infra/13-web-login-client.py`) and `http://localhost:8081/3lo/callback` on the OAuth workload identity (`infra/12-deploy-oauth-runtime.sh`).

## Deployed on AWS (`infra/14-deploy-webchat.sh`)
Both apps run unchanged as Lambdas behind API Gateway HTTP APIs (HTTPS, because Cognito only allows http callbacks for localhost). `lambda_adapter.py` replays each payload 2.0 event into the app's `BaseHTTPRequestHandler`.
- **Access:** Cognito sign-in only, with admin-created users. There's no IP allowlist yet; add one in front of the API. The Lambda resource policy allows only its own API; there's no Function URL and no public principal.
- **Sessions** are kept in memory, so each function has reserved concurrency 1. If the environment is recycled or redeployed, sign in again. A request made while another is still running gets HTTP 429. The HTTP API integration timeout is 30 s.
- The OAuth GUI's `CompleteResourceTokenAuth` runs as the function role `rsidc-webchat-role`, which also needs `GetSecretValue` on the 3LO provider secret.

## Tool RBAC GUI (`rbac_app.py`, port 8082 locally, `rsidc-webchat-rbac` on AWS)
Signs in on Cognito (OBO client, code + PKCE). The access token, which carries the `roles` claim from the Pre Token trigger, stays server-side.
For the demo gateway (Part 3) and the customer gateway (Part 4) it runs `tools/list`, then calls **every** catalogue tool directly. Each tool is shown as listed or hidden, and allowed or denied (a Cedar deny is HTTP 200 + `isError`).
Requests from the page are sent one at a time, because the Lambda has reserved concurrency 1.
- **Entra ID (Part 6):** "Sign in with Entra ID" (`/entra/login` → `/entra/callback`, public client with PKCE, separate `esid` cookie) adds a card for `rsidc-mall-entra-gateway`. The token's native `roles` claim comes from Entra App Roles. Requires the `ENTRA_*` and `ENTRA_GW_URL` env vars; without them the Entra card is hidden.

## Entra ID demo GUI (`entra_app.py`, port 8083 locally, `rsidc-webchat-entra` on AWS: https://se2shbmsej.execute-api.ap-southeast-1.amazonaws.com)
One page for the three Entra flows against runtime `rsidc_entra_agent`, the Entra counterpart of the GUIs above.
- **Sign in with Entra ID:** public client `rsidc-mall-test-client`, code + PKCE, scope `api://<rsidc-entra-agent>/access_as_user`. The token stays server-side (cookie `esid`); the page shows claims only. **Sign out** uses `logout_hint` and returns to `/entra/signed-out`.
- **Panels:**
  - **2LO:** app-only token and gateway table;
  - **OBO:** inbound vs outbound claims, the per-user gateway table, and Graph /me;
  - **3LO:** consent → `/3lo/callback` → `CompleteResourceTokenAuth` (the function role `rsidc-webchat-role` with the inline policy `webchat-entra`) → Token Vault → Graph /me.
- Requests are sent one at a time, because of reserved concurrency 1.
- **Users:** wei, ds1 and chen need Entra Security defaults disabled; lo3user works now (MFA code from `tests/totp.py`).
