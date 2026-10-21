# lambda/
`reporting/handler.py` is the AgentCore Gateway Lambda target for the 2LO test. It runs a fixed report on Redshift as the shared
service user `svc_reporting` (Data API + GetClusterCredentials), so the end user's identity is **not** propagated. Deployed by `../infra/11-2lo-gateway.sh`.

Part 3 (Gateway tool RBAC):
- `rbac_tools/`: tool A and tool B Lambda targets, deployed by `../infra/15-rbac-gateway.sh`.
- `pretoken/`: the Cognito Pre Token Generation trigger that turns IdC group mappings into a `roles` claim, deployed by `../infra/15-rbac-pretoken.py`.

Part 4 (customer version):
- `mall_tools/`: the customer's 4 mall tools as one Gateway Lambda target, deployed by `../infra/16-mall-gateway.sh`. `pretoken/` now also reads Cognito groups (`ROLE_SOURCES=cognito,idc`).
