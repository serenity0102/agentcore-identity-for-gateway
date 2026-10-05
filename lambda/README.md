# lambda/
`reporting/handler.py` is the AgentCore Gateway Lambda target for the 2LO test. It runs a fixed report on Redshift as the shared
service user `svc_reporting` (Data API + GetClusterCredentials), so the end user's identity is **not** propagated. Deployed by `../infra/11-2lo-gateway.sh`.
