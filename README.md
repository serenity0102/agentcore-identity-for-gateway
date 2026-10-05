# agentcore-identity-for-gateway

Validates that an **AgentCore Runtime** data agent querying/updating **Amazon Redshift** respects
**IAM Identity Center** access control end to end, via trusted identity propagation, with network access to Redshift restricted to the operator IP and the runtime egress IP.

- `RUNBOOK.md`: step-by-step reproduction, the real result of each step, findings, cost and teardown. **Start here.**
- `infra/`: idempotent provisioning scripts (`01`…`08`, `99-teardown`), IAM policies and SQL.
- `agent/`: the OBO data agent (Part 1) deployed to AgentCore Runtime.
- `agent_oauth/` + `lambda/`: the separate 2LO/3LO agent and the Gateway reporting Lambda (Part 2).
- `tests/`: the access matrix and the negative, network and exchange-boundary tests, with saved results.
- `docs/`: architecture diagram (SVG) and the email draft (PDF).
- `history/`: root-cause write-ups of the issues found while building this.
- `worklog.md`: change log.
