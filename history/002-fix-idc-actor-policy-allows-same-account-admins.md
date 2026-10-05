# 002: IdC app ActorPolicy did not stop same-account admins from exchanging user JWTs

## Problem
Test X1: IAM user `jacky` (admin, not the runtime role) called `CreateTokenWithIAM` with wei's JWT and
**received an IdC token for wei**. Anyone holding a captured, unredeemed user JWT and `sso-oauth:*` could act as that user in Redshift.

## Root cause
The ActorPolicy is a **resource-based policy**. Inside one account, an identity-based Allow
(`AdministratorAccess` includes `sso-oauth:*`) is enough on its own, so an Allow-only resource policy is not a boundary.

## Files
`infra/07-idc-agent-app.sh`: `put-application-authentication-method` ActorPolicy

## Changes
Added the statement `DenyEveryoneElseIncludingAdmins`: `Deny sso-oauth:CreateTokenWithIAM` for `Principal: *`
with the condition `ArnNotEquals aws:PrincipalArn = <runtime role>`. An explicit Deny overrides any identity-based Allow.

## Verification
X1 now returns `AccessDeniedException ... user/jacky is not authorized to perform: sso-oauth:CreateTokenWithIAM`.
X2 (runtime role) still succeeds, and the full matrix still passes 16/16.

## Possible improvements
Add an SCP that denies `sso-oauth:CreateTokenWithIAM` org-wide except for the approved agent roles.
