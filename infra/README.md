# infra/
Provisioning for the PoC. Run every script through `./run.sh` (it loads `00-config.sh` and `state.env`).
- `00-config.sh`: regions, IdC instance, names and operator IPs. `save` persists resource IDs to `state.env` (gitignored).
- `01`–`08`: numbered, idempotent steps. Re-running one is safe. See `../RUNBOOK.md` for the order and expected output.
- `99-teardown.sh`: deletes everything the steps created. It never touches the pre-existing IdC instance, users or groups.
- `policies/`: IAM trust and permission documents. `sql/`: admin seed data, grants to IdC group roles, RLS.
Conventions: tag everything `Project=rsidc`; no `0.0.0.0/0` ingress; no Redshift permissions on the runtime role.
