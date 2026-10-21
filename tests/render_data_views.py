"""Render the data-access evidence (admin full data + per-persona views from results-data-views.json)
as Markdown (RUNBOOK-cognito-idc.md, Part 4 · OBO, Step 5) and HTML (email) fragments: data/data-views.md, data/data-views.html."""
import html, json, os, time, boto3

D = os.path.dirname(os.path.abspath(__file__)); DOCS = os.path.join(D, "..", "data")
rs = boto3.Session(profile_name="default").client("redshift-data", region_name=os.environ["IDC_REGION"])

def admin(sql):
    r = rs.execute_statement(ClusterIdentifier=os.environ["REDSHIFT_CLUSTER_ID"], Database="dev", SecretArn=os.environ["REDSHIFT_ADMIN_SECRET_ARN"], Sql=sql)
    while rs.describe_statement(Id=r["Id"])["Status"] not in ("FINISHED", "FAILED", "ABORTED"): time.sleep(0.3)
    res = rs.get_statement_result(Id=r["Id"])
    return [c["name"] for c in res["ColumnMetadata"]], [[str(next(iter(v.values()))) for v in rec] for rec in res["Records"]]

TABLES = ["marketing.campaigns", "risk.credit_limits", "sales.orders"]
full = {t: admin(f"SELECT * FROM {t} ORDER BY 1") for t in TABLES}
views = json.load(open(os.path.join(D, "results-data-views.json")))
GROUP = {"wei": "risk-team", "zhang": "marketing-team", "chen": "platform-team", "ds1": "data-scientists"}
stamp = time.strftime("%Y-%m-%d")

def md_table(cols, rows):
    return "| " + " | ".join(cols) + " |\n|" + "|".join("---" for _ in cols) + "|\n" + "".join("| " + " | ".join(r) + " |\n" for r in rows)

def html_table(cols, rows, hide=()):
    th = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
    tr = "".join("<tr>" + "".join(f"<td>{html.escape(v)}</td>" for v in r) + "</tr>" for r in rows)
    return f"<table><tr>{th}</tr>{tr}</table>"

def cell(user, t):
    v = views[user]["tables"][t]
    if "denied" in v: return "denied", f"✗ {v['denied']}"
    total = len(full[t.split(' ')[0]][1]); cols = v["columns"]; all_cols = full[t.split(' ')[0]][0]
    note = f"{len(v['rows'])}/{total} rows"
    if len(cols) < len(all_cols): note += f", columns: {', '.join(cols)} (hidden: {', '.join(c for c in all_cols if c not in cols)})"
    return "ok", note

# ---------- Markdown ----------
md = [f"## Data in Redshift and who can see it (snapshot {stamp})\n",
      "Cluster `rsidc-cluster` (ap-east-1) → database **`dev`** → 3 user tables, 9 rows. The full data below was read as the admin (`rsadmin`), which bypasses RLS. "
      "Values that the matrix UPDATE cases modify (`budget`, `risk_score`) grow by +1 per matrix run.\n"]
for t in TABLES:
    md.append(f"**dev.{t}**\n\n" + md_table(*full[t]))
md.append("\n### What each persona gets back (same SQL, run through the OBO agent as that user)\n")
md.append("Regenerate with: `cd tests && ../infra/run.sh ../.venv/bin/python data_views.py && ../infra/run.sh ../.venv/bin/python render_data_views.py`\n")
qs = ["marketing.campaigns", "risk.credit_limits", "sales.orders (all columns)"]
md.append("| Persona (IdC group) | Redshift session user | " + " | ".join(f"`SELECT * FROM {q.split(' ')[0]}`" for q in qs) + " |\n|" + "---|" * (2 + len(qs)) + "\n"
          + "".join(f"| {u} ({GROUP[u]}) | `{views[u]['redshift_user']}` | " + " | ".join(cell(u, q)[1] for q in qs) + " |\n" for u in views))
z = views["zhang"]["tables"]["sales.orders (all columns)"]
md.append("\n**zhang: `SELECT * FROM sales.orders`** (RLS keeps only the APAC rows; the column grant **silently drops `customer_email`** from `SELECT *`; naming the column explicitly returns `42501 permission denied`)\n\n" + md_table(z["columns"], z["rows"]))
open(os.path.join(DOCS, "data-views.md"), "w").write("\n".join(md))

# ---------- HTML ----------
h = [f'<h3 style="font-size:11pt;margin:14px 0 6px;">2.2 Data in Redshift and who can see it <span class="small">(snapshot {stamp})</span></h3>',
     '<p>Cluster <code>rsidc-cluster</code> (ap-east-1) → database <b><code>dev</code></b> → 3 user tables, 9 rows. Full data, read as the admin (bypasses RLS):</p>']
for t in TABLES:
    h.append(f'<p class="small" style="margin:6px 0 2px"><b>dev.{t}</b></p>' + html_table(*full[t]))
h.append('<p style="margin-top:10px"><b>What each persona actually gets back.</b> The same <code>SELECT *</code>, run through the OBO agent as that user, gives this Redshift output:</p>')
rows = "".join(f"<tr><td>{u} ({GROUP[u]})</td><td><code>{html.escape(views[u]['redshift_user'])}</code></td>" +
               "".join(f'<td class="{"deny" if cell(u,q)[0]=="denied" else ""}">{html.escape(cell(u,q)[1])}</td>' for q in qs) + "</tr>" for u in views)
h.append("<table><tr><th>Persona (IdC group)</th><th>Redshift session user</th>" + "".join(f"<th>{q.split(' ')[0]}</th>" for q in qs) + "</tr>" + rows + "</table>")
h.append('<p class="small" style="margin:6px 0 2px"><b>zhang: <code>SELECT * FROM sales.orders</code></b>. RLS keeps only APAC rows, and the column grant <b>silently drops <code>customer_email</code></b> from <code>SELECT *</code>; naming the column explicitly returns <code>42501 permission denied</code>.</p>' + html_table(z["columns"], z["rows"]))
open(os.path.join(DOCS, "data-views.html"), "w").write("\n".join(h))
print("wrote data/data-views.md and data/data-views.html")
