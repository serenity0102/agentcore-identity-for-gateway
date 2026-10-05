"""AgentCore Gateway Lambda target for the 2LO test: runs a fixed report on Redshift as the shared
service user svc_reporting (Redshift Data API + GetClusterCredentials). The caller's identity is NOT propagated."""
import json, os, time, boto3

rsd = boto3.client("redshift-data", region_name=os.environ["REDSHIFT_REGION"])
SQL = "SELECT TRIM(current_user) AS redshift_user, order_id, region, customer_email, amount FROM sales.orders ORDER BY order_id"


def handler(event, context):
    tool = (context.client_context.custom or {}).get("bedrockAgentCoreToolName", "") if context.client_context else ""
    r = rsd.execute_statement(ClusterIdentifier=os.environ["REDSHIFT_CLUSTER_ID"], Database=os.environ["REDSHIFT_DB"],
                              DbUser="svc_reporting", Sql=SQL)
    while (d := rsd.describe_statement(Id=r["Id"]))["Status"] not in ("FINISHED", "FAILED", "ABORTED"):
        time.sleep(0.3)
    if d["Status"] != "FINISHED":
        return {"tool": tool, "error": d.get("Error")}
    res = rsd.get_statement_result(Id=r["Id"])
    cols = [c["name"] for c in res["ColumnMetadata"]]
    rows = [[next(iter(v.values())) for v in rec] for rec in res["Records"]]
    return {"tool": tool, "columns": cols, "rows": rows}
