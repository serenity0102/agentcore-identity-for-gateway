# agentcore-identity-for-gateway

Validates that an **AgentCore Runtime** data agent querying/updating **Amazon Redshift** respects
**IAM Identity Center** access control end to end, via trusted identity propagation, with network access to Redshift restricted to the operator IP and the runtime egress IP.

- `RUNBOOK-cognito-idc.md`: Cognito + IAM Identity Center, in four parts: Part 1 · Amazon Quick → Gateway (3LO by Quick), Part 2 · 3LO, Part 3 · 2LO, Part 4 · OBO (with per-user Gateway tool RBAC). Each step is collapsible.
- `infra/`: idempotent provisioning scripts (`01`…`08`, `99-teardown`), IAM policies and SQL.
- `agent_obo/`: the OBO data agent (Part 1) deployed to AgentCore Runtime.
- `agent_oauth/` + `lambda/`: the separate 2LO/3LO agent and the Gateway reporting Lambda (Part 2).
- `webchat/`: browser GUIs (OBO and 2LO/3LO); run locally or deploy behind API Gateway (HTTP API) → Lambda (`infra/14-deploy-webchat.sh`).
- `tests/`: the access matrix and the negative, network and exchange-boundary tests.

## ⚠️ Cost and disclaimer
- **This deploys billable AWS resources** in your account: a Redshift cluster, NAT gateways, AgentCore Runtime / Gateway / Identity, Lambda, API Gateway, Cognito and CloudWatch Logs. While it runs it costs about **$0.72/hour (~$17/day)**; see "Cost" in `RUNBOOK-cognito-idc.md`. Your bill may differ by Region, usage and pricing changes.
- **Tear down when you're done** to stop charges: run `infra/run.sh infra/99-teardown.sh` (steps 01–12), and follow the teardown step of each part in `RUNBOOK-cognito-idc.md` for the web GUIs (14), Gateway tool RBAC (15) and mall gateway (16). Then check the Billing console and Cost Explorer for anything left over. The teardown deletes Redshift **without a final snapshot**.
- **Disclaimer:** this is sample code for learning and testing, not production-ready. You're responsible for any cost it incurs, and for the security and compliance of anything you deploy with it. Review the scripts before you run them, and use a non-production account.


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
| Agent | `agent_oauth/` (`mode=2lo`) | `agent_oauth/` (`mode=3lo`) | `agent_obo/` |
| Token mechanism | `GetResourceOauth2Token(M2M)` → Cognito `client_credentials` | `GetResourceOauth2Token(USER_FEDERATION)` → consent → Token Vault | Cognito JWT → IdC `CreateTokenWithIAM` (trusted token issuer) |
| Identity seen by Redshift | `svc_reporting` (same rows for every user) | n/a (calls Cognito `userInfo` as the user) | `AWSIDC:<user>` (row-level security, grants per IdC group) |
