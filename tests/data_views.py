"""Evidence for permissions: what each persona actually gets back through the OBO agent, per table.
Writes tests/results-data-views.json (used by RUNBOOK.md and the email)."""
import json, os, uuid
from invoke import invoke
from tokens import id_token

QUERIES = {
  "marketing.campaigns": "SELECT * FROM marketing.campaigns ORDER BY 1",
  "risk.credit_limits":  "SELECT * FROM risk.credit_limits ORDER BY 1",
  "sales.orders (all columns)": "SELECT * FROM sales.orders ORDER BY 1",
  "sales.orders (non-PII columns)": "SELECT order_id, region, amount, order_date FROM sales.orders ORDER BY 1",
}
out = {}
for user in ("wei", "zhang", "chen", "ds1"):
    t, sid = id_token(user), f"rsidc-views-{user}-{uuid.uuid4()}"
    who = invoke(t, {"sql": "SELECT current_user"}, session_id=sid)[1]["result"]["rows"][0][0]
    out[user] = {"redshift_user": who, "tables": {}}
    for name, sql in QUERIES.items():
        r = invoke(t, {"sql": sql}, session_id=sid)[1]["result"]
        out[user]["tables"][name] = ({"columns": r["columns"], "rows": r["rows"]} if r.get("ok")
                                     else {"denied": r["error"].split("'M': '")[1].split("'")[0] if "'M': '" in r["error"] else r["error"]})
        print(f"{user:6} {name:32} -> {len(r['rows']) if r.get('ok') else 'DENIED'}")
json.dump(out, open(os.path.join(os.path.dirname(__file__), "results-data-views.json"), "w"), indent=1)
