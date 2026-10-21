"""AgentCore Gateway Lambda targets for the RBAC test (Part 3). One code base, two functions:
TOOL=sales -> get_sales_summary (region aggregates, no PII); TOOL=crm -> get_customer_contacts (customer emails, PII).
Runs on Redshift as the shared service user svc_reporting. Authorization happens at the Gateway (Cedar), not here."""
import os, time, boto3

rsd = boto3.client("redshift-data", region_name=os.environ["REDSHIFT_REGION"])
SQL = {
    "sales": "SELECT region, COUNT(*) AS orders, SUM(amount) AS total_amount FROM sales.orders GROUP BY region ORDER BY region",
    "crm": "SELECT order_id, customer_email FROM sales.orders ORDER BY order_id",
}[os.environ["TOOL"]]


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
