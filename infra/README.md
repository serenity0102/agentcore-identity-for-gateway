# infra/
Provisioning for the PoC. Run every script through `./run.sh` (it loads `00-config.sh` and `state.env`).

## Prerequisites / assumptions
- **IAM Identity Center is already enabled** in your AWS account (organization or account instance) in `IDC_REGION`. These scripts don't create or delete the IdC instance.
- **Set your IdC values in `00-config.sh`** before running anything:
  - `IDC_INSTANCE_ARN`: your instance ARN, `arn:aws:sso:::instance/ssoins-<id>` (IAM Identity Center console → Settings → Instance ARN, or `aws sso-admin list-instances --region <IDC_REGION>`);
  - `IDENTITY_STORE_ID`: the matching identity store ID, `d-<id>` (same command / page);
  - `IDC_REGION` and `RT_REGION` if you use other Regions.
- `ACCOUNT_ID` is looked up from your credentials (`aws sts get-caller-identity`); the profile is `AWS_PROFILE` in `00-config.sh`.

 regions, IdC instance, names and operator IPs. `save` persists resource IDs to `state.env` (gitignored).
- `01`–`08`: numbered, idempotent steps. Re-running one is safe. See `../RUNBOOK-cognito-idc.md` for the order and expected output.
- `99-teardown.sh`: deletes everything the steps created. It never touches the pre-existing IdC instance, users or groups.
- `policies/`: IAM trust and permission documents. `sql/`: admin seed data, grants to IdC group roles, RLS.
Conventions: tag everything `Project=rsidc`; no `0.0.0.0/0` ingress; no Redshift permissions on the runtime role.
- `15-rbac-*`, Part 3 (Gateway tool RBAC). Run in this order: `15-rbac-idc-groups.sh`, `15-rbac-gateway.sh`, `15-rbac-pretoken.py`, `15-rbac-policy.sh LOG_ONLY|ENFORCE`, `15-rbac-logs.sh`. It only *creates* project-owned IdC groups (`rsidc-gw-*`). Pre-existing IdC groups are read but never modified.
- `16-mall-*`, Part 4 (customer version, Amazon Quick → Gateway MCP → Lambda tools, RBAC from Cognito groups). Run in this order: `16-mall-cognito.py`, `15-rbac-pretoken.py` (adds the Cognito source and the `live` alias), `16-mall-gateway.sh`, `16-mall-logs.sh`, `16-mall-policy.sh LOG_ONLY|ENFORCE`.
