# 003: 3LO shared browser stores another user's token in the caller's vault slot

## Problem
In the 3LO test, temp user A's consent URL was opened in a browser that was already signed in to Cognito as wei.
Cognito silently reused wei's session and showed no login form. `CompleteResourceTokenAuth` with A's JWT succeeded, and
A's Token Vault slot then held **wei's** token, so the agent would act on wei's data for A.

## Root cause
Session binding (`CompleteResourceTokenAuth`) proves that the **app user** who started the flow is the one completing it.
It cannot know **which IdP account** the browser signed in with. The IdP's SSO cookie decided the identity.

## Files / code
- `agent_oauth/main.py`: `three_lo()`, plus `invoke()`, which reads the caller's email from the forwarded Authorization header
- `infra/12-deploy-oauth-runtime.sh`: `requestHeaderAllowlist: ["Authorization"]`
- `infra/09-cognito-oauth-clients.sh`: managed login v2 (required for `prompt=login`)
- `tests/oauth_tests.py`: risk, recovery, `prompt=login` and control scenarios with throwaway users

## Before
The agent trusted whatever token the vault returned.

## Changes
1. **Identity guard:** after obtaining the vault token, the agent calls `userInfo` and compares the email with the inbound JWT's email.
   On mismatch it returns `IDENTITY_MISMATCH` and no data.
2. Recovery path: a forced re-consent (`forceAuthentication=true`) in a clean browser replaces the stale token.
3. Tried `prompt=login` through `customParameters`. The login form is shown (v2), but no token was stored afterwards, so it is recorded as OBSERVED and not relied on.

## Why
The guard is a deterministic check of the actual outbound identity against the actual caller. It does not depend on IdP session behaviour.

## Verification
`oauth_tests.py`:
- `IDENTITY_MISMATCH` returned for the shared-browser case (PASS)
- recovery returns A's own token (PASS)
- control user C works (PASS)
- 18/18 asserted cases in total

## Possible improvements
- Confirm with the AgentCore Identity team whether `prompt`/`max_age` via `customParameters` should store the token.
- Bind the expected subject in the authorization request (`login_hint`) where the IdP supports it.
