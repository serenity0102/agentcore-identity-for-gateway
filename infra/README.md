# infra/
Provisioning for the PoC. Run every script through `./run.sh` (it loads `00-config.sh` and `state.env`).

## Prerequisites / assumptions
- **IAM Identity Center is already enabled** in your AWS account (organization or account instance) in `IDC_REGION`. These scripts don't create or delete the IdC instance.
- **Set your IdC values in `00-config.sh`** before running anything:
  - `IDC_INSTANCE_ARN`: your instance ARN, `arn:aws:sso:::instance/ssoins-<id>` (IAM Identity Center console → Settings → Instance ARN, or `aws sso-admin list-instances --region <IDC_REGION>`);
  - `IDENTITY_STORE_ID`: the matching identity store ID, `d-<id>` (same command / page);
  - `IDC_REGION` and `RT_REGION` if you use other Regions.
- **Deployment uses a named AWS CLI profile.** Set `AWS_PROFILE` in `00-config.sh` (default: `default`) to a profile in `~/.aws/config` with permissions to create the resources (IAM, VPC, Cognito, Redshift, AgentCore, Lambda, API Gateway). Check it with `aws sts get-caller-identity --profile <name>`.
- `ACCOUNT_ID` is looked up from that profile (`aws sts get-caller-identity`), so you don't set it.

- **IdC test users and groups already exist**: users `wei`, `zhang`, `chen`, `ds1` in the groups `risk-team`, `marketing-team`, `platform-team`, `data-scientists`. The IdC user's email must equal the email that `02-cognito.sh` gives the Cognito user (the trusted token issuer maps by email); edit the list in `02-cognito.sh` to match your IdC users.
- **Tools on the operator machine (macOS):** AWS CLI v2, [`uv`](https://docs.astral.sh/uv/), `zip`, `nc`, `curl`, `openssl`. The scripts use BSD `sed -i ''`, so on Linux change it to `sed -i`.

## Install the test environment
Run from the project root. Every step is idempotent: if one fails, fix the cause and re-run it. Resource IDs are saved to `infra/state.env`, and test-user passwords to `tests/.users.env` (both gitignored). Expected output and console checks for each step are in [`../RUNBOOK-cognito-idc.md`](../RUNBOOK-cognito-idc.md).

**0. Python venv** (used by the Python steps and the tests):
```bash
cd agent_obo && uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt requests && cd ..
PY=agent_obo/.venv/bin/python
```

**1. Shared foundation + OBO** (Cognito JWT → IdC → Redshift as the user):
```bash
infra/run.sh ./infra/01-runtime-network.sh          # VPC, NAT, fixed egress IP for the runtimes
infra/run.sh ./infra/02-cognito.sh                  # user pool (admin-create only), OBO client, 4 users
infra/run.sh ./infra/03-idc-redshift-app.sh         # IdC trusted token issuer + Redshift IdC application
infra/run.sh ./infra/04-redshift-cluster.sh         # Redshift ra3.large; SG = operator IPs + runtime egress IP only (~10 min)
infra/run.sh $PY infra/05-seed-redshift.py          # tables, grants to IdC group roles, RLS
infra/run.sh ./infra/06-runtime-role.sh             # runtime execution role (no Redshift permissions)
infra/run.sh ./infra/07-idc-agent-app.sh            # customer-managed IdC app for the agent token exchange
infra/run.sh ./infra/08-deploy-runtime.sh           # agent_obo/ -> AgentCore Runtime rsidc_data_agent
cd tests && ../infra/run.sh ../$PY validate_matrix.py && cd ..   # expect 16/16
```

**2. 2LO and 3LO** (AgentCore Identity: client credentials, user consent + Token Vault):
```bash
infra/run.sh ./infra/09-cognito-oauth-clients.sh    # Cognito domain, resource server, 2LO + 3LO clients
infra/run.sh $PY infra/10-credential-providers.py   # credential providers rsidc-2lo-cognito / rsidc-3lo-cognito
infra/run.sh ./infra/11-2lo-gateway.sh              # 2LO Gateway -> lambda/reporting -> Redshift svc_reporting
infra/run.sh ./infra/12-deploy-oauth-runtime.sh     # agent_oauth/ -> runtime rsidc_oauth_agent
cd tests && ../infra/run.sh ../$PY oauth_tests.py && cd ..       # expect 18/18 (3LO opens a browser for consent)
```

**3. Web GUIs** (optional; API Gateway HTTP API → Lambda):
```bash
infra/run.sh $PY infra/13-web-login-client.py       # localhost callbacks for running the GUIs locally
infra/run.sh bash infra/14-deploy-webchat.sh        # deploy the GUIs and register their callback URLs; prints the URLs
```

**4. Gateway per-user tool RBAC** (optional; demo with IdC groups):
```bash
infra/run.sh ./infra/15-rbac-idc-groups.sh          # creates project-owned IdC groups rsidc-gw-* only
infra/run.sh ./infra/15-rbac-gateway.sh             # Gateway + lambda/rbac_tools targets
infra/run.sh $PY infra/15-rbac-pretoken.py          # Cognito Pre Token trigger -> roles claim (alias "live")
infra/run.sh ./infra/15-rbac-policy.sh ENFORCE      # Cedar policies (use LOG_ONLY first to dry-run)
cd tests && ../infra/run.sh ../$PY rbac_tests.py enforce && cd ..
```

**5. Customer version: Amazon Quick → mall gateway** (optional; RBAC from Cognito groups):
```bash
infra/run.sh $PY infra/16-mall-cognito.py           # Cognito groups, Quick app client, resource server
infra/run.sh $PY infra/15-rbac-pretoken.py          # re-run: adds Cognito groups as a role source
infra/run.sh ./infra/16-mall-gateway.sh             # Gateway rsidc-mall-gateway + lambda/mall_tools
infra/run.sh ./infra/16-mall-policy.sh ENFORCE
infra/run.sh $PY tests/mall_rbac_tests.py enforce   # expect 25/25
```
Then connect Amazon Quick as described in [`../data/quick-mcp-connector.md`](../data/quick-mcp-connector.md).

**6. Agent Registry** (optional): `infra/run.sh $PY infra/17-agent-registry.py` (add `REGISTRY_REGION=us-east-1` for Quick in us-east-1).

**Teardown:** `infra/run.sh ./infra/99-teardown.sh` removes steps 01–12. For 14–16, follow the teardown step of each part in the runbook. See the cost note in [`../README.md`](../README.md).

## Files
- `00-config.sh`: regions, IdC instance, names and operator IPs. `save` persists resource IDs to `state.env` (gitignored).
- `01`–`08`: numbered, idempotent steps. Re-running one is safe. See `../RUNBOOK-cognito-idc.md` for the order and expected output.
- `99-teardown.sh`: deletes everything the steps created. It never touches the pre-existing IdC instance, users or groups.
- `lambda/`: code for the Lambdas these scripts deploy: `reporting` (11, 2LO Gateway target), `rbac_tools` (15), `mall_tools` + `tools.json` (16), `pretoken` (15-rbac-pretoken.py, Cognito trigger).
- `policies/`: IAM trust and permission documents. `sql/`: admin seed data, grants to IdC group roles, RLS.
Conventions: tag everything `Project=rsidc`; no `0.0.0.0/0` ingress; no Redshift permissions on the runtime role.
- `15-rbac-*`, Part 3 (Gateway tool RBAC). Run in this order: `15-rbac-idc-groups.sh`, `15-rbac-gateway.sh`, `15-rbac-pretoken.py`, `15-rbac-policy.sh LOG_ONLY|ENFORCE`, `15-rbac-logs.sh`. It only *creates* project-owned IdC groups (`rsidc-gw-*`). Pre-existing IdC groups are read but never modified.
- `16-mall-*`, Part 4 (customer version, Amazon Quick → Gateway MCP → Lambda tools, RBAC from Cognito groups). Run in this order: `16-mall-cognito.py`, `15-rbac-pretoken.py` (adds the Cognito source and the `live` alias), `16-mall-gateway.sh`, `16-mall-logs.sh`, `16-mall-policy.sh LOG_ONLY|ENFORCE`.
