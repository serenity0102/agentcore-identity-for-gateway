OBO enforces IdC per-user access in Redshift (16/16 matrix). The runtime role has no Redshift permission; every session runs as `AWSIDC:<user>`.
External JWTs are single-use at IdC; the agent exchanges once per sign-in (history/001).
An Allow-only IdC app ActorPolicy did not stop same-account admins; fixed with an explicit Deny (history/002, verified in step 7).
2LO bypasses per-user controls by design: every user, including one with no grants, saw all rows with PII via `svc_reporting` (step 11).
3LO: Token Vault isolation and session binding work; a shared IdP browser session can store another user's token, mitigated by the agent identity guard (history/003). `prompt=login` via customParameters stored no token (observed).
Console pitfalls (recorded in the aws-deploy-evidence skill): IdC tabs don't change the URL; Gateway deep links redirect to home; IAM inline policies must be expanded; full-page shots can hide a field behind the sticky footer.
