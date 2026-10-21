# RUNBOOK · Microsoft Entra ID × Amazon Bedrock AgentCore Identity (2LO / 3LO / OBO)

This runbook covers **only the Microsoft Entra ID** variants (originally RUNBOOK Part 7, "Microsoft Entra ID × AgentCore Identity (2LO / 3LO / OBO)", plus Parts 6 / 6b). The Cognito + IAM Identity Center variants (and the shared AWS foundation: VPC, Redshift, IdC, web GUIs, Agent Registry) are in [RUNBOOK-cognito-idc.md](RUNBOOK-cognito-idc.md).
Each part starts with an overview table of all its steps; click a step to expand its full content (purpose, commands, **actual result**, how to verify, teardown). Passwords, client secrets and TOTP seeds are never written here: they stay in the gitignored `tests/.entra-users.env`, `tests/.entra-agent.env` and `tests/.entra-totp.env`.

## Contents
- [Demo access: web GUIs and test accounts](#demo-access-web-guis-and-test-accounts)
- [0 · Shared foundation](#shared-foundation) · 5 steps
- [Part 1 · 2LO — Entra ID + 2LO (client credentials) through AgentCore Identity](#part-1-2lo) · 5 steps
- [Part 2 · 3LO — Entra ID + 3LO (AgentCore Identity USER_FEDERATION)](#part-2-3lo) · 6 steps
- [Part 3 · OBO — Entra ID + OBO (On-Behalf-Of) via AgentCore Identity](#part-3-obo) · 10 steps
- [Appendix](#appendix) · 3 steps

<a id="shared-foundation"></a>

## Demo access: web GUIs and test accounts

> **Passwords are not in this file.** Read them with `cat tests/.entra-users.env` (gitignored), or open the local copy
> `RUNBOOK-entra-id.local.md` (gitignored, includes the passwords). Rotate them after the demo.

| Web GUI | URL | What it demos |
|---|---|---|
| **Entra demo GUI** | https://se2shbmsej.execute-api.ap-southeast-1.amazonaws.com | "Sign in with Entra ID" → **2LO** panel · **OBO** panel (plus OBO → Graph /me) · **3LO** panel (consent → Token Vault → Graph /me) · "Sign out of Entra ID" |
| RBAC GUI, Entra card | https://80l9l7cdk2.execute-api.ap-southeast-1.amazonaws.com | "Sign in with Entra ID" → "Check tools" on `rsidc-mall-entra-gateway` (per-user Gateway tool RBAC) |

| User (UPN) | Password | MFA | App Roles (rsidc-mall-api) | Expected in the GUI |
|---|---|---|---|---|
| `lo3user@tojackywugmail.onmicrosoft.com` | see `tests/.entra-users.env` (`ENTRA_PW_LO3USER`) | TOTP: run `agent/.venv/bin/python tests/totp.py` and type the 6-digit code | none | 2LO: 2 tools (the app's roles) · OBO: 0 tools · 3LO: Graph /me = lo3user |
| `wei@tojackywugmail.onmicrosoft.com` | see `tests/.entra-users.env` (`ENTRA_PW_WEI`) | needs Security defaults **off** (see below) | List, Footfall, Hourly, Zone | OBO: 4 tools |
| `ds1@tojackywugmail.onmicrosoft.com` | see `tests/.entra-users.env` (`ENTRA_PW_DS1`) | needs Security defaults **off** | List, Footfall | OBO: 2 tools (hourly and zone denied) |
| `chen@tojackywugmail.onmicrosoft.com` | see `tests/.entra-users.env` (`ENTRA_PW_CHEN`) | needs Security defaults **off** | none | OBO: 0 tools |

- **Interactive sign-in:** the tenant's **Security defaults** force MFA registration on interactive sign-in. Until they're turned off (Entra admin center → Identity → Overview → Properties → Manage security defaults → Disabled), only `lo3user` can sign in to the GUIs.
- **Scripted tests don't need MFA:** `tests/entra_identity_tests.py` and `tests/entra_demo.py` use non-interactive sign-in, so they work for every user.

## 0 · Shared foundation

**Architecture overview.** All three flows go through ONE AgentCore Identity credential provider (`rsidc-entra`, MicrosoftOauth2) and the runtime `rsidc_entra_agent`, which trusts Entra as its inbound IdP. Animated walkthrough: [docs/flow-rbac.html](docs/flow-rbac.html) (open the "Entra ID · App Roles" tab).

| Flow | Diagram | Part |
|---|---|---|
| 2LO (client credentials, app-only token) | ![Entra 2LO architecture](docs/architecture-entra-2lo.svg) | [Part 1 · 2LO](#part-1-2lo) |
| 3LO (user consent + Token Vault → Graph) | ![Entra 3LO architecture](docs/architecture-entra-3lo.svg) | [Part 2 · 3LO](#part-2-3lo) |
| OBO (On-Behalf-Of token exchange → per-user Gateway) | ![Entra OBO architecture](docs/architecture-entra-obo.svg) | [Part 3 · OBO](#part-3-obo) |


| # | Step | Purpose | Result |
|---|---|---|---|
| 1 | [Prerequisites and cost](#found-step-1) | tools, tenant sign-in, what it costs | Entra ID Free only; no Azure subscription resources |
| 2 | [Entra setup: `infra/18-entra-setup.py` (apps, App Roles, users, assignments)](#found-step-2) | the resource app, test client, users and App Role assignments | rsidc-mall-api 99a0f5bd…, test client 650791ca…, users wei / ds1 / chen |
| 3 | [Agent app + AgentCore side: `infra/19-entra-agent-setup.py` and `infra/20-entra-agentcore.sh`](#found-step-3) | the agent's Entra app, ONE credential provider, the runtime | provider rsidc-entra (MicrosoftOauth2) · runtime rsidc_entra_agent-TbPbf79MRf |
| 4 | [Security defaults and MFA (read before any interactive demo)](#found-step-4) | why interactive sign-in needs MFA now | 3LO uses lo3user + TOTP; wei / ds1 / chen need Security defaults off |
| 5 | [Results overview](#found-step-5) | all three flows at once | 2LO 7/7 · 3LO 5/5 (×2) · OBO 10/10 |
| 6 | [Entra demo web GUI (2LO / 3LO / OBO in one page)](#found-step-6) | demo all three flows in a browser | https://se2shbmsej.execute-api.ap-southeast-1.amazonaws.com · lo3user tested end to end |

<details id="found-step-1"><summary><b>Step 1 · Prerequisites and cost</b> · result: Entra ID Free only; no Azure subscription resources</summary>

**Purpose:** cover the deck's three patterns (slides 32–53) with Entra ID as the IdP, through **one** AgentCore Identity credential provider. Entra at the Gateway's inbound auth (per-user tool RBAC) is covered in Part 3 · step 9 of this runbook.

- **Tools:** Azure CLI (`az`), signed in as a Global Administrator of the tenant; the project venv (`agent/.venv`); `agent-browser` for the interactive 3LO consent.
- **Sign-in:** `az login --tenant a32ee4b2-31ac-4e1f-97e7-683e1ae0702a --allow-no-subscriptions` as a Global Administrator.
- **Cost:** Entra side, **Entra ID Free only**: app registrations, users, App Roles and per-user assignments. No resources are created in the Azure subscription, and no P2 trial is started. AWS side: one gateway plus one policy engine, billed per request (negligible). Part 7 adds one runtime (`rsidc_entra_agent`, billed per invocation) and one credential provider.

</details>

<details id="found-step-2"><summary><b>Step 2 · Entra setup: <code>infra/18-entra-setup.py</code> (apps, App Roles, users, assignments)</b> · result: rsidc-mall-api 99a0f5bd…, test client 650791ca…, users wei / ds1 / chen</summary>

```bash
agent/.venv/bin/python infra/18-entra-setup.py           # Entra: apps, App Roles, users, assignments (Graph)
```
**Actual result (2026-10-07):**

- **Entra:**
  - `rsidc-mall-api` appId `99a0f5bd-4b55-4ded-b2be-0677614373b7` (v2 tokens, scope `mcp.access`, 4 App Roles);
  - `rsidc-mall-test-client` `650791ca-1a7f-4170-bedd-d2ee901e67d4` (public client, admin-consented);
  - users wei, ds1 and chen @tojackywugmail.onmicrosoft.com;
  - assignments: wei has 4 roles, ds1 has List + Footfall, chen has none.
- **Token claims:** `ver=2.0`, `aud=99a0f5bd-4b55-4ded-b2be-0677614373b7`, `azp=<client>`, `roles` native. chen's token has **no** `roles` claim.

</details>

<details id="found-step-3"><summary><b>Step 3 · Agent app + AgentCore side: <code>infra/19-entra-agent-setup.py</code> and <code>infra/20-entra-agentcore.sh</code></b> · result: provider rsidc-entra (MicrosoftOauth2) · runtime rsidc_entra_agent-TbPbf79MRf</summary>

**Deployed** (new resources only; nothing existing was changed):
- **Entra (Free):**
  - app `rsidc-entra-agent` (`fffe808b-63a9-4de8-91ef-1a44ef9a1276`): the agent's API (`api://…/access_as_user`, v2 tokens) and the OAuth client. Its secret is in AgentCore Identity and in the gitignored `tests/.entra-agent.env`;
  - app roles Tools.Mall.List and Footfall granted to the app (for 2LO);
  - delegated Graph User.Read and mall `mcp.access`, with admin consent;
  - App Roles on `rsidc-mall-api` now also allow `Application`.
- **AgentCore:**
  - credential provider `rsidc-entra` (MicrosoftOauth2, tenant `a32ee4b2-31ac-4e1f-97e7-683e1ae0702a`), with callback `https://bedrock-agentcore.ap-southeast-1.amazonaws.com/identities/oauth2/callback/27705e14-8441-4a25-a10a-d2a1e47b8bf4` registered as a web redirect;
  - runtime `rsidc_entra_agent-TbPbf79MRf` (PUBLIC network; inbound customJWTAuthorizer with Entra v2 discovery, audience `rsidc-entra-agent`);
  - role `rsidc-entra-runtime-role` (this provider and its secret only).
```bash
agent/.venv/bin/python infra/19-entra-agent-setup.py          # Entra side (Graph)
ROOT_DIR=$PWD bash infra/20-entra-agentcore.sh                # provider + role + runtime
infra/run.sh agent/.venv/bin/python tests/entra_identity_tests.py 2lo   # each phase is independent (parallel-safe)
infra/run.sh agent/.venv/bin/python tests/entra_identity_tests.py obo
infra/run.sh agent/.venv/bin/python tests/entra_identity_tests.py 3lo   # interactive consent via agent-browser
```

</details>

<details id="found-step-4"><summary><b>Step 4 · Security defaults and MFA (read before any interactive demo)</b> · result: 3LO uses lo3user + TOTP; wei / ds1 / chen need Security defaults off</summary>

- **MFA:** Entra **Security defaults** now force MFA registration on interactive sign-in (the "Skip for now" period is over). 3LO uses a dedicated user `lo3user` with a TOTP authenticator (seed only in the gitignored `tests/.entra-totp.env`). wei, ds1 and chen still can't sign in interactively, for example in the GUI, until Security defaults are turned off in the portal or each user registers Authenticator.

</details>

<details id="found-step-5"><summary><b>Step 5 · Results overview</b> · result: 2LO 7/7 · 3LO 5/5 (×2) · OBO 10/10</summary>

**Results (2026-10-19):**

| Flow | Result | What it proves |
|---|---|---|
| 2LO | **7/7** | an app-only token (`azp` = agent, roles = the app's List + Footfall, no user); every user gets the same 2 tools |
| OBO | **10/10** | the exchanged token carries the **user** (`preferred_username`, the user's own roles): wei 4 tools, ds1 2, chen 0; OBO to Graph `/me` = ds1 |
| 3LO | **5/5**, two runs | CONSENT_REQUIRED → Entra sign-in → callback → `CompleteResourceTokenAuth` → TOKEN_FROM_VAULT, Graph `/me` = lo3user; wei (no consent) still gets CONSENT_REQUIRED |

**Regression:** Part 6 `entra_rbac_tests.py enforce` still 19/19.

**Issues hit:**
- **Network:** a transient Graph/S3 connection reset (re-run).
- **IAM policy:** a `sed`-generated policy was invalid JSON (now written explicitly).
- **MFA:** see step 4.

</details>

<details id="found-step-6"><summary><b>Step 6 · Entra demo web GUI (2LO / 3LO / OBO in one page)</b> · result: https://se2shbmsej.execute-api.ap-southeast-1.amazonaws.com · lo3user tested end to end</summary>

**Purpose:** one browser page to demo all three Entra flows against runtime `rsidc_entra_agent`, the Entra counterpart of the Cognito + IdC GUIs. Code: `webchat/entra_app.py` + `webchat/entra_index.html`, served by `webchat/lambda_adapter.py` (Lambda `rsidc-webchat-entra` behind its own API Gateway HTTP API).

- **Sign in with Entra ID:** public client `rsidc-mall-test-client`, code + PKCE, scope `openid profile offline_access api://<rsidc-entra-agent>/access_as_user`, `prompt=login`. The access token (aud = rsidc-entra-agent) stays server-side in memory (HttpOnly cookie `esid`); the page shows claims only.
- **Sign out:** Entra `/logout` with `logout_hint` and `post_logout_redirect_uri = <GUI>/entra/signed-out` → "✓ Signed out".
- **Panels:** **2LO** ("Run 2LO": app-only token claims + gateway table) · **OBO** ("Exchange on behalf of me": inbound vs outbound claims + per-user gateway table; "OBO → Microsoft Graph /me") · **3LO** ("Connect my Microsoft profile (3LO)" → Entra consent → `/3lo/callback` → `CompleteResourceTokenAuth` with the user's token → TOKEN_FROM_VAULT + Graph /me + identity guard; "force re-consent", "Check vault only").

**Deploy** (part of the shared webchat deploy; additive):
```bash
infra/run.sh bash infra/14-deploy-webchat.sh     # 4th function "entra" → WEB_ENTRA_URL in infra/state.env
```
It also: adds `<GUI>/entra/callback` and `<GUI>/entra/signed-out` to the test client (via `infra/18-entra-setup.py`, `WEB_ENTRA_URL`), merges `<GUI>/3lo/callback` into the Entra agent's workload-identity return URLs (keeps `http://localhost:8765/callback`), and puts a separate inline policy `webchat-entra` on `rsidc-webchat-role` (`CompleteResourceTokenAuth` on the Entra workload identity + `rsidc-entra`, `GetSecretValue` on the provider secret; see history/004).

**Actual result (2026-10-20), browser end to end as lo3user:**

| Panel | Result |
|---|---|
| Sign-in | signed in as lo3user@tojackywugmail.onmicrosoft.com (MFA code from `tests/totp.py`) |
| 2LO | HTTP 200 · no user in the token · roles = [Tools.Mall.List, Tools.Mall.Footfall] · listed: footfall + list |
| OBO | inbound aud = rsidc-entra-agent → outbound aud = rsidc-mall-api · user kept (lo3user) · roles none → 0 tools (lo3user has no App Roles: expected) |
| OBO → Graph | HTTP 200 · /me = lo3user |
| 3LO | consent completed · CompleteResourceTokenAuth OK · TOKEN_FROM_VAULT · identity guard passes · Graph /me = lo3user |
| Sign-out | back on the GUI, "Signed out of the app and of Microsoft Entra ID" |

Regression after the deploy: all 4 GUIs return 200; `entra_identity_tests.py 2lo` 7/7, `obo` 10/10; `entra_rbac_tests.py enforce` 19/19.

**Demo note:** wei / ds1 / chen can sign in here only after Entra Security defaults are disabled (Step 4); until then use lo3user (OBO shows 0 tools for lo3user because no App Role is assigned to it, which itself demonstrates per-user enforcement).

**Teardown:** delete Lambda `rsidc-webchat-entra` and its HTTP API (same loop as the Cognito runbook's webchat teardown), the inline policy `webchat-entra` on `rsidc-webchat-role`, and the two `/entra/*` redirect URIs on the test client.

</details>

<a id="part-1-2lo"></a>

## Part 1 · 2LO — Entra ID + 2LO (client credentials) through AgentCore Identity

**Demo in the GUI:** https://se2shbmsej.execute-api.ap-southeast-1.amazonaws.com → sign in → **2LO** panel → "Run 2LO".

![Entra ID 2LO architecture](docs/architecture-entra-2lo.svg)

*Steps 1–7: user signs in to Entra → runtime inbound auth (Entra JWT, aud = rsidc-entra-agent) → WAT → `GetResourceOauth2Token(M2M)` → Entra client_credentials returns an app-only token (roles = the app's List + Footfall) → Gateway inbound JWT check (JWKS) → Cedar → Lambda. Outbound identity = the agent, not the user.*

**Purpose:** the agent calls a protected resource as **itself**, with no user in the token. A Microsoft Entra ID app-only token is obtained through the AgentCore Identity Credential Provider (`oauth2Flow=M2M`). The resource is the Entra-trusting Gateway `rsidc-mall-entra-gateway`, whose Cedar rules match the `roles` claim. Every caller gets the same tools, because the token carries the agent app's App Roles, not the user's.

| # | Step | Purpose | Result |
|---|---|---|---|
| 1 | [Mapping to the deck (slides 32–39, Direct External 3LO/2LO)](#step-2lo-1) | each deck caption (slides 32–39) → what we built | 7 deck steps mapped |
| 2 | [Commands](#step-2lo-2) | deploy and run the 2LO phase | 3 commands |
| 3 | [Actual result (2026-10-19): 7/7 PASS (`tests/results/entra_identity_2lo.json`)](#step-2lo-3) | measured result | PASS 7/7 · app-only token, same 2 tools for everyone |
| 4 | [How to verify](#step-2lo-4) | check it yourself | credential provider = MicrosoftOauth2 |
| 5 | [Teardown](#step-2lo-5) | remove the 2LO resources | runtime, provider, role, Entra app |

<details id="step-2lo-1"><summary><b>Step 1 · Mapping to the deck (slides 32–39, Direct External 3LO/2LO)</b> · result: 7 deck steps mapped</summary>

| Deck caption | What we built |
|---|---|
| 33 App authenticates: JWT via IdP (user-delegated) or SigV4 | The user signs in to Entra (test client `rsidc-mall-test-client`), with scope `api://<rsidc-entra-agent>/access_as_user` |
| 34 App invokes agent via Runtime → Authorizer validates credentials | Runtime `rsidc_entra_agent`, customJWTAuthorizer: discovery = tenant v2 metadata, allowedAudience = `fffe808b-…` (rsidc-entra-agent) |
| 35 Identity Directory → Runtime obtains WAT (agent + user) | The runtime injects the workload access token (`BedrockAgentCoreContext.get_workload_access_token()`) |
| 36 Agent presents WAT to Credential Provider → OAuth flow | `get_resource_oauth2_token(provider="rsidc-entra" (MicrosoftOauth2), oauth2Flow="M2M", scopes=["api://<rsidc-mall-api>/.default"])` |
| 37 2LO: client credentials → external IdP issues resource token | Entra issues an **app-only** v2 token: `aud` = rsidc-mall-api, `azp` = rsidc-entra-agent, `roles` = the app's App Roles (Tools.Mall.List, Tools.Mall.Footfall); no `preferred_username` or `scp` |
| 38 Resource token in Token Vault | M2M tokens are cached by AgentCore Identity for the agent; no per-user consent |
| 39 Agent calls external resource directly | The agent calls `rsidc-mall-entra-gateway` MCP `tools/list` and `tools/call` with the app-only token; Cedar allows List + Footfall |

</details>

<details id="step-2lo-2"><summary><b>Step 2 · Commands</b> · result: 3 commands</summary>

```bash
agent/.venv/bin/python infra/19-entra-agent-setup.py      # Entra: app rsidc-entra-agent + app roles List/Footfall (application permissions)
ROOT_DIR=$PWD infra/run.sh bash infra/20-entra-agentcore.sh   # credential provider rsidc-entra + runtime rsidc_entra_agent
infra/run.sh agent/.venv/bin/python tests/entra_identity_tests.py 2lo
```

</details>

<details id="step-2lo-3"><summary><b>Step 3 · Actual result (2026-10-19): 7/7 PASS (<code>tests/results/entra_identity_2lo.json</code>)</b> · result: PASS 7/7 · app-only token, same 2 tools for everyone</summary>

| Case | Expected | Actual |
|---|---|---|
| wei / ds1 / chen: 2LO token is app-only | no user, no scp, azp = agent | ✓ (all three) |
| wei / ds1 / chen: tools/list = the app's roles | list + footfall | ✓ (all three, identical); hourly and zone denied on direct call |
| No bearer → runtime rejects | 401/403 | 401 |

Key outbound claims, the same for every caller:
- `aud=99a0f5bd-…` (rsidc-mall-api)
- `azp=fffe808b-…` (rsidc-entra-agent)
- `roles=["Tools.Mall.List","Tools.Mall.Footfall"]`
- no `preferred_username` or `scp`

That is the 2LO property: the user's identity (wei can use 4 tools, chen 0) does **not** reach the resource. Compare with OBO (Part 3 of this runbook, `docs/part7/obo.md`).

</details>

<details id="step-2lo-4"><summary><b>Step 4 · How to verify</b> · result: credential provider = MicrosoftOauth2</summary>

- Re-run the test command above.
- `aws bedrock-agentcore-control get-oauth2-credential-provider --name rsidc-entra --region ap-southeast-1 --query credentialProviderVendor` returns `MicrosoftOauth2`.
- Entra admin center → Enterprise applications → rsidc-mall-api → Users and groups: rsidc-entra-agent holds Tools.Mall.List and Tools.Mall.Footfall.

</details>

<details id="step-2lo-5"><summary><b>Step 5 · Teardown</b> · result: runtime, provider, role, Entra app</summary>

Part 7 resources: runtime `rsidc_entra_agent`, credential provider `rsidc-entra`, IAM role `rsidc-entra-runtime-role`, S3 prefix `agent_entra/`, and Entra app `rsidc-entra-agent` (`az ad app delete --id fffe808b-63a9-4de8-91ef-1a44ef9a1276`). The App Roles on rsidc-mall-api keep `allowedMemberTypes=[Application, User]` (additive; Part 6 is unaffected).

</details>

<a id="part-2-3lo"></a>

## Part 2 · 3LO — Entra ID + 3LO (AgentCore Identity USER_FEDERATION)

**Demo in the GUI:** https://se2shbmsej.execute-api.ap-southeast-1.amazonaws.com → sign in (lo3user) → **3LO** panel → "Connect my Microsoft profile (3LO)".

![Entra ID 3LO architecture](docs/architecture-entra-3lo.svg)

*Steps 1–8: LOGIN 1 (user signs in to Entra) → runtime inbound auth (Entra JWT) → `GetResourceOauth2Token(USER_FEDERATION)` returns CONSENT_REQUIRED + authorizationUrl → LOGIN 2 (consent at Entra) → AgentCore callback → return URL with session_id → `CompleteResourceTokenAuth` binds the token to (agent, user) in the Token Vault → TOKEN_FROM_VAULT → Microsoft Graph `/me` as the user, with an identity guard.*

**Purpose:** the agent acts **as the user** on an external API (Microsoft Graph) after a one-time consent. The user's token is kept in the AgentCore Token Vault per (agent, user); the agent calls Graph directly (no Gateway).

| # | Step | Purpose | Result |
|---|---|---|---|
| 1 | [Mapping to the deck (slides 32–39, "Direct External", 3LO)](#step-3lo-1) | each deck step (slides 32–39) → what we built | 7 deck steps mapped |
| 2 | [Commands](#step-3lo-2) | run the 3LO phase (drives the browser) | 1 command, ~2–3 min |
| 3 | [Actual result (2026-10-19), two consecutive runs, both 5/5 PASS](#step-3lo-3) | measured result, two runs | PASS 5/5 ×2 · Graph /me = lo3user |
| 4 | [Findings (important for the demo)](#step-3lo-4) | MFA, one-time request_uri, headless MFA page | 3 findings |
| 5 | [How to verify](#step-3lo-5) | check it yourself | callback URL registered as Web redirect |
| 6 | [Teardown](#step-3lo-6) | remove lo3user and its files | lo3user + TOTP file |

<details id="step-3lo-1"><summary><b>Step 1 · Mapping to the deck (slides 32–39, "Direct External", 3LO)</b> · result: 7 deck steps mapped</summary>

| Deck step | What we built |
|---|---|
| 33 App authenticates (JWT via IdP) | User gets an Entra v2 token for the agent API: `aud = rsidc-entra-agent (fffe808b-63a9-4de8-91ef-1a44ef9a1276)`, `scp = access_as_user` |
| 34 Runtime authorizer validates JWT | Runtime `rsidc_entra_agent` (`rsidc_entra_agent-TbPbf79MRf`): `customJWTAuthorizer` with the Entra v2 discovery URL, `allowedAudience = [fffe808b-63a9-4de8-91ef-1a44ef9a1276]` |
| 35 Runtime obtains WAT (agent + user) | The runtime injects the workload access token bound to (rsidc_entra_agent, the user) |
| 36 Agent presents WAT to Credential Provider | `GetResourceOauth2Token(oauth2Flow=USER_FEDERATION, provider=rsidc-entra, scopes=[User.Read, offline_access], resourceOauth2ReturnUrl=http://localhost:8765/callback)` |
| 37 3LO: user consents via browser | AgentCore returns `authorizationUrl` + `sessionUri` → the user signs in to Entra (consent was admin-granted for User.Read) → Entra → AgentCore callback (`https://bedrock-agentcore.ap-southeast-1.amazonaws.com/identities/oauth2/callback/27705e14-8441-4a25-a10a-d2a1e47b8bf4`, registered as a web redirect on rsidc-entra-agent) → redirect to the return URL with `session_id` → the app calls `CompleteResourceTokenAuth(sessionUri, userToken = the user's inbound Entra token)` (session binding) |
| 38 Resource token in Token Vault | Stored per (agent, user); a 2nd user (wei) without consent still gets `CONSENT_REQUIRED` |
| 39 Agent calls external resource | `GET https://graph.microsoft.com/v1.0/me` with the vault token. **Identity guard:** Graph `userPrincipalName` must equal the inbound `preferred_username`, else `IDENTITY_MISMATCH` |

</details>

<details id="step-3lo-2"><summary><b>Step 2 · Commands</b> · result: 1 command, ~2–3 min</summary>

```bash
infra/run.sh agent/.venv/bin/python tests/entra_identity_tests.py 3lo     # ~2–3 min, drives the browser itself
```
Credential provider: `rsidc-entra` (vendor `MicrosoftOauth2`, tenant a32ee4b2-31ac-4e1f-97e7-683e1ae0702a, client rsidc-entra-agent). Agent code: `agent_entra/main.py` (`three_lo`). Infra: `infra/19-entra-agent-setup.py`, `infra/20-entra-agentcore.sh`.

</details>

<details id="step-3lo-3"><summary><b>Step 3 · Actual result (2026-10-19), two consecutive runs, both 5/5 PASS</b> · result: PASS 5/5 ×2 · Graph /me = lo3user</summary>

| Case | Result |
|---|---|
| First call → `CONSENT_REQUIRED` (authorizationUrl + sessionUri) | PASS |
| Consent completed → AgentCore redirected to the return URL with `session_id` | PASS |
| `CompleteResourceTokenAuth` binds the session to the signed-in user | PASS |
| Token from the vault → Graph `/me` = `lo3user@tojackywugmail.onmicrosoft.com` (`TOKEN_FROM_VAULT`, HTTP 200) | PASS |
| wei (no consent of their own) → `CONSENT_REQUIRED` (the vault is per (agent, user)) | PASS |

Results file: `tests/results/entra_identity_3lo.json`.

</details>

<details id="step-3lo-4"><summary><b>Step 4 · Findings (important for the demo)</b> · result: 3 findings</summary>

1. **MFA registration blocks interactive Entra sign-in.** The tenant uses *Security defaults*. Interactive sign-in for wei/ds1/chen, and even a brand-new user, now shows "Let's keep your account secure" with **no "Skip for now"**, so users must register an authenticator. Token flows that use ROPC (the 2LO/OBO tests, Part 3 · step 9) are unaffected.
   - **This also affects interactive Entra login in the RBAC web GUI (Part 3 · step 10 of this runbook):** a human must register Microsoft Authenticator once per user.
   - For automation, a **dedicated** 3LO test user `lo3user@tojackywugmail.onmicrosoft.com` was created and registered with an authenticator app (TOTP). Its seed is only in `tests/.entra-totp.env` (gitignored), and `tests/totp.py` generates the code. Shared users and the tenant policy were not changed.
2. **One-time `request_uri`.** Launching the browser and navigating in a single call can load AgentCore's hosted `/identities/oauth2/authorize?request_uri=…` twice, and the second load answers `Invalid request`. The test opens `about:blank` first. If `Invalid request` still appears, it requests a fresh consent URL (up to 3 tries; 0 were needed in the final runs).
3. **Headless MFA registration page.** `mysignins.microsoft.com/register` sometimes stays on "enable JavaScript" or returns `BadRequest` in headless Chrome. A reload fixes it.

</details>

<details id="step-3lo-5"><summary><b>Step 5 · How to verify</b> · result: callback URL registered as Web redirect</summary>

- Re-run the command above and expect `5/5 PASS`.
- `aws bedrock-agentcore-control get-oauth2-credential-provider --name rsidc-entra --region ap-southeast-1 --query '{vendor:credentialProviderVendor,callback:callbackUrl}'`
- Entra admin center → App registrations → rsidc-entra-agent → Authentication shows the AgentCore callback URL as a Web redirect.

</details>

<details id="step-3lo-6"><summary><b>Step 6 · Teardown</b> · result: lo3user + TOTP file</summary>

- **Entra:** `az ad user delete --id lo3user@tojackywugmail.onmicrosoft.com`, then delete `tests/.entra-totp.env` and the `ENTRA_PW_LO3USER` line in `tests/.entra-users.env`.
- **Shared Part 7 resources:** runtime, provider and the rsidc-entra-agent app are torn down together, per Appendix step 1 of this runbook.

</details>

<a id="part-3-obo"></a>

## Part 3 · OBO — Entra ID + OBO (On-Behalf-Of) via AgentCore Identity

**Demo in the GUI:** https://se2shbmsej.execute-api.ap-southeast-1.amazonaws.com → sign in → **OBO** panel → "Exchange on behalf of me" and "OBO → Microsoft Graph /me".

![Entra ID OBO architecture](docs/architecture-entra-obo.svg)

*Steps 1–8: user signs in to Entra (aud = rsidc-entra-agent, scp = access_as_user) → runtime inbound auth → WAT bound to the user → `GetResourceOauth2Token(ON_BEHALF_OF_TOKEN_EXCHANGE)` → AgentCore Identity runs Entra OBO (RFC 7523 jwt-bearer, `requested_token_use=on_behalf_of`) → new token aud = rsidc-mall-api with the SAME user and the user's roles → Gateway → Cedar per user (wei 4 · ds1 2 · chen 0 tools) → Lambda; optional OBO to Graph `/me`. The downstream it is used against is shown in step 9 below.*

| # | Step | Purpose | Result |
|---|---|---|---|
| 1 | [Purpose](#obo-step-1) | what OBO means here | user token → downstream-scoped token, no consent |
| 2 | [Deck mapping (Agentcore Identity Deep Dive, slides 48–53)](#obo-step-2) | each deck slide (48–53) → what we did | 5 deck steps mapped |
| 3 | [How it is built](#obo-step-3) | Entra side, AWS side, agent code | provider rsidc-entra · runtime rsidc_entra_agent |
| 4 | [Commands](#obo-step-4) | deploy and run the OBO phase | 3 commands |
| 5 | [Actual result (2026-10-19): 10/10 PASS (`tests/results/entra_identity_obo.json`)](#obo-step-5) | measured result + claims before/after | PASS 10/10 · aud → rsidc-mall-api, user kept |
| 6 | [How to verify](#obo-step-6) | check it yourself | re-runnable, read-only |
| 7 | [Not done](#obo-step-7) | what was not built and why | Entra → IdC → Redshift |
| 8 | [Teardown (Part 7)](#obo-step-8) | remove the OBO resources | runtime, provider, Entra app |
| 9 | [Per-user enforcement downstream (Gateway tool RBAC with Entra) · Entra ID version of the tool RBAC (Microsoft Entra ID → Gateway, no Cognito)](#obo-step-9) | the downstream the OBO token is used against · diagram: [architecture-rbac-entra.svg](docs/architecture-rbac-entra.svg) · animation: [flow-rbac.html](docs/flow-rbac.html) (Entra tab) | log_only 15/15 · enforce 19/19 · change 4/4 |
| 10 | [Entra ID sign-in in the RBAC web GUI (sign-in and sign-out)](#obo-step-10) | show the per-user result in a browser | wei 4 · ds1 2 · chen 0 tools; sign-out returns 401 |

<details id="obo-step-1"><summary><b>Step 1 · Purpose</b> · result: user token → downstream-scoped token, no consent</summary>

The agent calls a downstream API **as the signed-in user**, with no extra consent prompt. The AgentCore Identity **Credential Provider** exchanges the user's inbound Entra token for a downstream-scoped token, so the downstream (AgentCore Gateway + Cedar) can enforce per-user access.

</details>

<details id="obo-step-2"><summary><b>Step 2 · Deck mapping (Agentcore Identity Deep Dive, slides 48–53)</b> · result: 5 deck steps mapped</summary>

| Slide | Caption | What we did |
|---|---|---|
| 49 | User signs in via IdP → app receives JWT | The user signs in to Entra ID (tenant `a32ee4b2-31ac-4e1f-97e7-683e1ae0702a`) and gets a v2 access token, `aud` = `rsidc-entra-agent` (`fffe808b-63a9-4de8-91ef-1a44ef9a1276`), `scp` = `access_as_user` |
| 50 | App invokes agent via Runtime → Authorizer validates JWT | Runtime `rsidc_entra_agent` (`rsidc_entra_agent-TbPbf79MRf`): `customJWTAuthorizer` with Entra v2 discovery, `allowedAudience` = agent appId |
| 51 | Runtime obtains the WAT (binds agent + user) | The runtime hands the agent a workload access token bound to the inbound user token (`BedrockAgentCoreContext.get_workload_access_token()`) |
| 52 | Agent presents WAT to Credential Provider → requests OBO token exchange | `GetResourceOauth2Token(oauth2Flow=ON_BEHALF_OF_TOKEN_EXCHANGE, provider=rsidc-entra, scopes=[api://<rsidc-mall-api>/mcp.access])` |
| 53 | Credential Provider exchanges inbound user token for downstream-scoped resource token (RFC 8693 / 7523) | Provider `rsidc-entra` (vendor `MicrosoftOauth2`) runs Entra's OBO flow: **JWT_AUTHORIZATION_GRANT (RFC 7523 jwt-bearer)**, `assertion` = the inbound user token, `requested_token_use=on_behalf_of` added automatically, client auth = `rsidc-entra-agent` id + secret (stored by AgentCore Identity, never seen by the agent) |

The exchanged token then calls **`rsidc-mall-entra-gateway`**, where Cedar evaluates the **user's** `roles`. A second OBO scope, `User.Read`, calls Microsoft Graph `/me` as the user.

</details>

<details id="obo-step-3"><summary><b>Step 3 · How it is built</b> · result: provider rsidc-entra · runtime rsidc_entra_agent</summary>

- **Entra side:** `infra/19-entra-agent-setup.py` (Graph, Entra ID Free).
  - App `rsidc-entra-agent`: exposes `access_as_user`, v2 tokens, admin-consented delegated `rsidc-mall-api/mcp.access` + Graph `User.Read`.
  - The test client may request `access_as_user`.
- **AWS side:** `infra/20-entra-agentcore.sh`.
  - Credential provider `rsidc-entra` (MicrosoftOauth2, tenantId, clientId/secret).
  - Role `rsidc-entra-runtime-role`, scoped to this provider, its secret and its workload identity.
  - Runtime `rsidc_entra_agent` (PUBLIC network, Entra JWT inbound).
- **Agent code:** `agent_entra/main.py`, modes `obo` and `obo_graph`. The agent never sees the client secret or performs the exchange itself.

</details>

<details id="obo-step-4"><summary><b>Step 4 · Commands</b> · result: 3 commands</summary>

```bash
agent/.venv/bin/python infra/19-entra-agent-setup.py
ROOT_DIR=$PWD infra/run.sh bash infra/20-entra-agentcore.sh
infra/run.sh agent/.venv/bin/python tests/entra_identity_tests.py obo
```

</details>

<details id="obo-step-5"><summary><b>Step 5 · Actual result (2026-10-19): 10/10 PASS (<code>tests/results/entra_identity_obo.json</code>)</b> · result: PASS 10/10 · aud → rsidc-mall-api, user kept</summary>

| User | OBO token `preferred_username` | roles (from Entra App Role assignments) | tools/list via Gateway | direct calls |
|---|---|---|---|---|
| wei | wei@tojackywugmail.onmicrosoft.com | List, Zone, Hourly, Footfall | 4 tools | all allowed |
| ds1 | ds1@tojackywugmail.onmicrosoft.com | List, Footfall | list + footfall | hourly, zone **denied** (isError) |
| chen | chen@tojackywugmail.onmicrosoft.com | (none) | none | all denied |
| ds1 → Graph `/me` (OBO, `User.Read`) | | | | HTTP 200, `userPrincipalName` = ds1@… |

**Claims before and after the exchange (wei):**

| | Inbound (to the runtime) | Outbound (from AgentCore Identity OBO) |
|---|---|---|
| aud | `fffe808b-63a9-4de8-91ef-1a44ef9a1276` (rsidc-entra-agent) | `99a0f5bd-4b55-4ded-b2be-0677614373b7` (rsidc-mall-api) |
| azp | test client `650791ca-1a7f-4170-bedd-d2ee901e67d4` | `fffe808b-63a9-4de8-91ef-1a44ef9a1276` (the agent is the actor) |
| scp | `access_as_user` | `mcp.access` |
| preferred_username | wei@… | wei@… (the user is preserved) |
| roles | — | the user's App Roles: List, Zone, Hourly, Footfall |

**Contrast with 2LO:** with the same agent and the same gateway, the M2M token always carries the **app's** roles (List + Footfall), whoever the user is. With OBO, the downstream sees and enforces **the user**.

**Regression:** the step 9 suite `tests/entra_rbac_tests.py enforce` is still 19/19 after the `rsidc-mall-api` App Roles were extended to `allowedMemberTypes = [User, Application]`.

</details>

<details id="obo-step-6"><summary><b>Step 6 · How to verify</b> · result: re-runnable, read-only</summary>

- `infra/run.sh agent/.venv/bin/python tests/entra_identity_tests.py obo`: re-runnable and read-only (each call uses its own runtime session).
- `aws bedrock-agentcore-control get-oauth2-credential-provider --name rsidc-entra --region ap-southeast-1 --query credentialProviderVendor` returns `MicrosoftOauth2`.
- Gateway decisions are logged in the CloudWatch log group `/aws/vendedlogs/bedrock-agentcore/gateway/rsidc-mall-entra-gateway`.

</details>

<details id="obo-step-7"><summary><b>Step 7 · Not done</b> · result: Entra → IdC → Redshift</summary>

Entra → IAM Identity Center → Redshift (the Part 1 pattern with an Entra-trusting TTI) was not built. The IdC users' emails (`@techfinance.example.com`) don't match the Entra UPNs, and changing the shared IdC instance is risky.

</details>

<details id="obo-step-8"><summary><b>Step 8 · Teardown (Part 7)</b> · result: runtime, provider, Entra app</summary>

1. Delete runtime `rsidc_entra_agent-TbPbf79MRf`, credential provider `rsidc-entra`, and role `rsidc-entra-runtime-role`.
2. Entra: `az ad app delete --id fffe808b-63a9-4de8-91ef-1a44ef9a1276`.
3. Optionally revert the `rsidc-mall-api` App Roles to `allowedMemberTypes = [User]`.

</details>

<details id="obo-step-9"><summary><b>Step 9 · Per-user enforcement downstream (Gateway tool RBAC with Entra) · Entra ID version of the tool RBAC (Microsoft Entra ID → Gateway, no Cognito)</b> · result: log_only 15/15 · enforce 19/19 · change 4/4</summary>

![Entra ID Gateway tool RBAC architecture](docs/architecture-rbac-entra.svg)

*Entra App Roles → native `roles` claim in the access token → Gateway inbound auth (Entra v2 JWKS, allowedAudience = rsidc-mall-api) → Policy in AgentCore (Cedar, one fixed rule per tool) → Lambda. Animated: [docs/flow-rbac.html](docs/flow-rbac.html), "Entra ID · App Roles" tab.*

The OBO token from step 5 (and an Entra user token signed in directly) is sent to `rsidc-mall-entra-gateway`, whose Cedar rules read the **user's** `roles` claim. This step is how that downstream was built and tested (originally RUNBOOK Part 6).

**Purpose:** this is the downstream the OBO token above is used against. It is the same per-user tool RBAC as the Cognito customer version (see RUNBOOK-cognito-idc.md), with **Microsoft Entra ID** as the IdP. Entra's native App Role claim `roles` drives the Cedar rules, so there is no Cognito and no Pre Token trigger.
**Cost:** Entra side, **Entra ID Free only**: app registrations, users, App Roles and per-user assignments. No resources are created in the Azure subscription, and no P2 trial is started. AWS side: one gateway plus one policy engine, billed per request (negligible).
**Prereq:** `az login --tenant a32ee4b2-31ac-4e1f-97e7-683e1ae0702a --allow-no-subscriptions` as a Global Administrator.
```bash
agent/.venv/bin/python infra/18-entra-setup.py           # Entra: apps, App Roles, users, assignments (Graph)
infra/run.sh bash infra/18-entra-gateway.sh LOG_ONLY       # Gateway trusting Entra + policy engine
infra/run.sh agent/.venv/bin/python tests/entra_rbac_tests.py log_only
infra/run.sh bash infra/18-entra-gateway.sh ENFORCE
infra/run.sh agent/.venv/bin/python tests/entra_rbac_tests.py enforce
infra/run.sh agent/.venv/bin/python tests/entra_rbac_tests.py change   # adds, then removes, ds1's Hourly assignment
```
**Actual result (2026-10-07):**
- **Entra:**
  - `rsidc-mall-api` appId `99a0f5bd-4b55-4ded-b2be-0677614373b7` (v2 tokens, scope `mcp.access`, 4 App Roles);
  - `rsidc-mall-test-client` `650791ca-1a7f-4170-bedd-d2ee901e67d4` (public client, admin-consented);
  - users wei, ds1 and chen @tojackywugmail.onmicrosoft.com;
  - assignments: wei has 4 roles, ds1 has List + Footfall, chen has none.
- **Token claims:** `ver=2.0`, `aud=99a0f5bd-4b55-4ded-b2be-0677614373b7`, `azp=<client>`, `roles` native. chen's token has **no** `roles` claim.
- **Gateway** `rsidc-mall-entra-gateway-xmcsl34bfw`: discovery `https://login.microsoftonline.com/a32ee4b2-31ac-4e1f-97e7-683e1ae0702a/v2.0/.well-known/openid-configuration`, allowedAudience = API appId. Policy engine `rsidc_mall_entra_pe-0e_t3_2i4s` (ENFORCE) with 4 policies `entra_mall_*`.
- **Tests:**
  - **log_only 15/15:** everyone can call everything; Cedar only logs.
  - **enforce 19/19:**
    - wei can use 4 tools, ds1 2, chen 0; hidden tools return `isError`;
    - tampered token → 403, Cognito token → 403, Graph token (`aud` = graph) → 403, garbage → 401.
  - **change 4/4:** adding the Hourly assignment for ds1 shows up in a new token **12 s** later; the old token stays denied; the assignment is restored.
- **Cognito regression after this step** (suites in RUNBOOK-cognito-idc.md): mall 25/25, IdC-group RBAC 12/12, OBO 16/16; all 3 web GUIs return 200.
- **Issues hit:**
  1. Policy names are unique across the Region, not per engine, so they are prefixed `entra_`.
  2. The shared gateway role needed a **separate** inline policy `entra-gateway` for the new engine (the Cognito customer-version policy is untouched). The first attach failed on IAM propagation; a retry loop handles it.
  3. The Graph wrong-audience test must request `.default`, because the test client has no `User.Read` grant.
**How you can verify:** `aws bedrock-agentcore-control get-gateway --gateway-identifier rsidc-mall-entra-gateway-xmcsl34bfw --region ap-southeast-1 --query '{auth:authorizerConfiguration,policy:policyEngineConfiguration}'`. Diagram: `docs/architecture-rbac-entra.svg`. Animation: `docs/flow-rbac.html`, tab "Entra ID".
**Teardown:**
- **AWS:** detach the policy engine, then delete gateway target `mall`, gateway `rsidc-mall-entra-gateway-xmcsl34bfw`, the 4 `entra_mall_*` policies, policy engine `rsidc_mall_entra_pe-0e_t3_2i4s`, and the inline policy `entra-gateway` on `rsidc-mall-gateway-role`.
- **Entra:** `az ad app delete --id 99a0f5bd-4b55-4ded-b2be-0677614373b7`, `az ad app delete --id 650791ca-1a7f-4170-bedd-d2ee901e67d4`, `az ad user delete --id wei@tojackywugmail.onmicrosoft.com` (likewise ds1 and chen).

</details>

<details id="obo-step-10"><summary><b>Step 10 · Entra ID sign-in in the RBAC web GUI (sign-in and sign-out)</b> · result: wei 4 · ds1 2 · chen 0 tools; sign-out returns 401</summary>

The same GUI (`https://80l9l7cdk2.execute-api.ap-southeast-1.amazonaws.com`) now has an **"Sign in with Entra ID"** card.
- **Sign-in:** public client `rsidc-mall-test-client`, code + PKCE, scope `openid profile api://<appId>/mcp.access`, redirect `https://80l9l7cdk2.execute-api.ap-southeast-1.amazonaws.com/entra/callback` (added by `infra/18-entra-setup.py`).
- **Session:** a separate session cookie (`esid`) keeps the token server-side. The Cognito sign-in and its two cards are unchanged.
- **Deploy:** `infra/run.sh bash infra/14-deploy-webchat.sh`, which passes `ENTRA_*` and `ENTRA_GW_URL` to `rsidc-webchat-rbac`.

**Actual result (2026-10-07), browser end to end** (Entra sign-in → Check tools on `rsidc-mall-entra-gateway`):

| Entra user | roles claim | list / footfall / hourly / zone |
|---|---|---|
| wei | List, Zone, Hourly, Footfall | ✓ / ✓ / ✓ / ✓ |
| ds1 | List, Footfall | ✓ / ✓ / hidden + denied / hidden + denied |
| chen | (none) | all hidden + denied |

Regression: Cognito ds1 on the same GUI still gets ✓ list / ✓ footfall / ✗ hourly / ✗ zone on the customer gateway.
**Passwords:** the Entra test users' passwords are in `tests/.entra-users.env` (local only, gitignored).

**Entra sign-out (added 2026-10-07):** the "Sign out of Entra ID" button calls `/entra/logout`. That clears the app session (the `esid` cookie and the server-side token) and redirects to the Entra v2 `/logout` endpoint with:
- `logout_hint` (from the ID token's `login_hint` optional claim, added by `infra/18-entra-setup.py`), so Entra signs out the right account without the account picker;
- `post_logout_redirect_uri = <GUI>/entra/signed-out`, a registered redirect URI, which returns to the GUI with "✓ Signed out".

Actual result: signed in as ds1 → Sign out → back at `…/?entra=signed-out#entra` with "Signed out of the app and of Microsoft Entra ID". After a reload, the page shows "Sign in with Entra ID", and `POST /api/check/entra` without a session returns 401. No account picker appeared, even with 3 Entra accounts signed in in the same browser.

Issue found: the first attempt used `post_logout_redirect_uri=/`, which isn't registered, so Entra stayed on its own page. With only `id_token_hint`, Entra still showed "Pick an account".

</details>

<a id="appendix"></a>

## Appendix

| # | Step | Purpose | Result |
|---|---|---|---|
| 1 | [Full Entra teardown (AWS resources first, then Entra)](#app-step-1) | remove everything, in order | 6 ordered steps |
| 2 | [Decks](#app-step-2) | the three per-pattern decks | 2LO · 3LO · OBO pptx (gitignored) |
| 3 | [Cognito + IAM Identity Center version](#app-step-3) | the same patterns with Cognito and IdC | RUNBOOK-cognito-idc.md |

<details id="app-step-1"><summary><b>Step 1 · Full Entra teardown (AWS resources first, then Entra)</b> · result: 6 ordered steps</summary>

Run in this order; every item comes from the per-part teardown notes above.
1. **AWS · Part 1–3 agent:** delete runtime `rsidc_entra_agent-TbPbf79MRf`, credential provider `rsidc-entra` (its client secret is stored by AgentCore Identity), IAM role `rsidc-entra-runtime-role`, and the S3 prefix `agent_entra/`.
2. **AWS · Part 3 step 9 gateway:** detach the policy engine, then delete gateway target `mall`, gateway `rsidc-mall-entra-gateway-xmcsl34bfw`, the 4 `entra_mall_*` policies, policy engine `rsidc_mall_entra_pe-0e_t3_2i4s`, and the inline policy `entra-gateway` on `rsidc-mall-gateway-role`.
3. **AWS · RBAC web GUI:** redeploy `infra/14-deploy-webchat.sh` without the `ENTRA_*` variables (or tear the GUI down with the Cognito runbook).
4. **Entra · apps:** `az ad app delete --id fffe808b-63a9-4de8-91ef-1a44ef9a1276` (rsidc-entra-agent), `az ad app delete --id 99a0f5bd-4b55-4ded-b2be-0677614373b7` (rsidc-mall-api), `az ad app delete --id 650791ca-1a7f-4170-bedd-d2ee901e67d4` (rsidc-mall-test-client).
5. **Entra · users:** `az ad user delete --id wei@tojackywugmail.onmicrosoft.com` (likewise ds1, chen) and `az ad user delete --id lo3user@tojackywugmail.onmicrosoft.com`.
6. **Local files:** delete `tests/.entra-users.env`, `tests/.entra-agent.env` and `tests/.entra-totp.env`.

Per-part teardown notes as originally recorded:
**Teardown:**
- **AWS:** delete runtime `rsidc_entra_agent-TbPbf79MRf`, credential provider `rsidc-entra` and role `rsidc-entra-runtime-role`.
- **Entra:** `az ad app delete --id fffe808b-63a9-4de8-91ef-1a44ef9a1276`; also delete user `lo3user`.

</details>

<details id="app-step-2"><summary><b>Step 2 · Decks</b> · result: 2LO · 3LO · OBO pptx (gitignored)</summary>

**Decks:** [`docs/AgentCore-Identity-2LO.pptx`](docs/AgentCore-Identity-2LO.pptx) / [`-3LO.pptx`](docs/AgentCore-Identity-3LO.pptx) / [`-OBO.pptx`](docs/AgentCore-Identity-OBO.pptx) (see `docs/decks/README.md`).
Each deck has the Entra ID implementation next to the Cognito + IdC one. The decks are gitignored (they contain test passwords).

</details>

<details id="app-step-3"><summary><b>Step 3 · Cognito + IAM Identity Center version</b> · result: RUNBOOK-cognito-idc.md</summary>

See [RUNBOOK-cognito-idc.md](RUNBOOK-cognito-idc.md) for the same 2LO / 3LO / OBO patterns with Amazon Cognito and IAM Identity Center (including the Redshift trusted-identity-propagation OBO).

</details>

