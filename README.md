# agentcore-identity-for-gateway

Validates that an **AgentCore Runtime** data agent querying/updating **Amazon Redshift** respects
**IAM Identity Center** access control end to end, via trusted identity propagation, with network access to Redshift restricted to the operator IP and the runtime egress IP.

- `RUNBOOK.md`: step-by-step reproduction, the real result of each step, findings, cost and teardown. **Start here.**
- `infra/`: idempotent provisioning scripts (`01`…`08`, `99-teardown`), IAM policies and SQL.
- `agent/`: the OBO data agent (Part 1) deployed to AgentCore Runtime.
- `agent_oauth/` + `lambda/`: the separate 2LO/3LO agent and the Gateway reporting Lambda (Part 2).
- `webchat/`: browser GUIs (OBO and 2LO/3LO); run locally or deploy as IP-allowlisted Lambda Function URLs (`infra/14-deploy-webchat.sh`).
- `tests/`: the access matrix and the negative, network and exchange-boundary tests, with saved results.
- `docs/`: architecture diagram (SVG) and the email draft (PDF).
- `history/`: root-cause write-ups of the issues found while building this.
- `worklog.md`: change log.

## 2LO vs 3LO vs OBO

| Aspect | 2-Legged OAuth | 3-Legged OAuth | On-Behalf-Of (OBO) |
|---|---|---|---|
| Parties involved | 2 (App + Service) | 3 (User + App + Service) | 3+ (User → App → Service chain) |
| User consent required | ❌ No | ✅ Yes (explicit grant) | ✅ Yes (initial, then flows down) |
| User involved | ❌ No | ✅ Yes (actively grants permission) | ✅ Yes (but indirectly) |
| Authentication flow | Server-to-server only | User → redirect → login → consent | User token → App token → Service token |
| Use case | Automated/scheduled tasks, webhooks, service integrations | User login ("Sign in with Google"), app accessing user data | App accessing downstream services on behalf of the user |
| Token exchange | App signs request with own credentials | Authorization code → Access token | User's access token → new token with different scopes/permissions |
| Identity preserved | App's identity only | User's identity | User's identity (passed through the chain) |
| Common in | OAuth 1.0 (legacy), some enterprise APIs | OAuth 2.0 (modern standard) | OAuth 2.0, Microsoft/Azure, AWS Bedrock agents |
| Example | Cron job calling API nightly | "Login with GitHub" in your app | Agent calling AWS Lambda on behalf of the logged-in user |
| Security model | Credentials shared between services | User never shares credentials; app gets limited token | User delegates, identity chain validated at each step |
| Revocation | Service-level (remove API key) | User can revoke anytime in account settings | User revokes original grant; cascades down |

How each one maps to this repo:

| | 2LO | 3LO | OBO |
|---|---|---|---|
| Agent | `agent_oauth/` (`mode=2lo`) | `agent_oauth/` (`mode=3lo`) | `agent/` |
| Token mechanism | `GetResourceOauth2Token(M2M)` → Cognito `client_credentials` | `GetResourceOauth2Token(USER_FEDERATION)` → consent → Token Vault | Cognito JWT → IdC `CreateTokenWithIAM` (trusted token issuer) |
| Identity seen by Redshift | `svc_reporting` (same rows for every user) | n/a (calls Cognito `userInfo` as the user) | `AWSIDC:<user>` (row-level security, grants per IdC group) |
