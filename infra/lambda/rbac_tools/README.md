# infra/lambda/rbac_tools/
Two AgentCore Gateway Lambda targets for Part 3, sharing one code base and selected by `TOOL`. Deployed by `../../infra/15-rbac-gateway.sh`.
- `rsidc-tool-sales` (`TOOL=sales`): tool A `get_sales_summary`, region totals with no PII.
- `rsidc-tool-crm` (`TOOL=crm`): tool B `get_customer_contacts`, customer emails (PII).

Both query Redshift as `svc_reporting`. They contain **no** authorization code: who may call which tool is decided at the Gateway by Policy in AgentCore (Cedar).
