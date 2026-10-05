# 001: Redshift EXT_JWT fails on the second connection (single-use JWT)

## Problem
In the access matrix the first query per user succeeded, and every later query failed with
`FATAL 28000 Token credentials expired or invalid`. That turned 6 ALLOW cases into DENY and
produced several false-positive DENY passes.

## Root cause
IAM Identity Center treats an external IdP JWT as a **single-use assertion** (it tracks the `jti`).
With `token_type=EXT_JWT`, Redshift performs that exchange on **every new connection**, so the
second connection presented an already-redeemed JWT. After switching to CreateTokenWithIAM, the error became explicit:
`InvalidGrantException: JWT is already redeemed`.

## Files / code
- `agent/redshift_tools.py`: `connect_as_user`, new `idc_access_token`
- `infra/07-idc-agent-app.sh` (new): customer-managed IdC app (jwt-bearer grant, `redshift:connect`, ActorPolicy)
- `infra/08-deploy-runtime.sh`: env `IDC_REGION`, `AGENT_IDC_APP_ARN`
- `tests/validate_matrix.py`: stricter DENY check, one runtime session per user

## Before
The agent passed the raw Cognito JWT to Redshift on each tool call, which only works for one connection per JWT.
The test also counted connection failures as "DENY = PASS".

## Changes
1. The agent exchanges the JWT **once** via `sso-oauth:CreateTokenWithIAM` against the customer-managed app, caches the IdC access token keyed by sha256(JWT) until expiry, and connects with `ACCESS_TOKEN`.
2. The runtime role is allowed `CreateTokenWithIAM` on that one app only.
3. A matrix DENY passes only on `stage=execute` with `permission denied`.
4. The tests use one runtime session per user (one conversation per sign-in).

## Why
This is the standard trusted-identity-propagation pattern for custom applications. The IdC access token is reusable for about an hour,
and the exchange is bound to a single, auditable principal.

## Verification
`validate_matrix.py`: 16/16. `negative_tests.py` N3 shows that replaying a JWT in a new session is rejected, as designed.

## Possible improvements
- Persist the IdC token or refresh token outside the microVM (for example, an encrypted DynamoDB item keyed by session) so new sessions don't need a re-sign-in.
- Have the client send a freshly refreshed Cognito token per new session.
