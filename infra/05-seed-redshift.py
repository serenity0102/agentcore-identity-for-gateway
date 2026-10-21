"""Seed tables + IdC-group grants as the Redshift admin via the Data API (admin secret from Secrets Manager).
The Data API is IAM-authenticated and does not traverse the cluster security group; it is used ONLY for admin setup."""
import os, sys, time, boto3

rs = boto3.Session().client("redshift-data", region_name=os.environ["IDC_REGION"])
sql = open(os.path.join(os.path.dirname(__file__), "sql", sys.argv[1] if len(sys.argv) > 1 else "01-seed-and-grants.sql")).read()
stmts = [s.strip() for s in "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--")).split(";") if s.strip()]
for s in stmts:
    r = rs.execute_statement(ClusterIdentifier=os.environ["REDSHIFT_CLUSTER_ID"], Database=os.environ["REDSHIFT_DB"],
                             SecretArn=os.environ["REDSHIFT_ADMIN_SECRET_ARN"], Sql=s)
    while (d := rs.describe_statement(Id=r["Id"]))["Status"] not in ("FINISHED", "FAILED", "ABORTED"):
        time.sleep(0.5)
    status = d["Status"] if d["Status"] == "FINISHED" else f'{d["Status"]}: {d.get("Error")}'
    print(f"[{status}] {s.splitlines()[0][:90]}")
    if d["Status"] != "FINISHED" and "already" not in str(d.get("Error")):
        sys.exit(1)
