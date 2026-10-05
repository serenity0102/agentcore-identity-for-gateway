"""Insert AWS console screenshots (docs/img/console/*.png + manifest.tsv with the exact URL at capture time)
into RUNBOOK.md (under each step) and docs/email-draft.html (Appendix A). Idempotent via markers.
Run from the project root: python3 docs/build_console_shots.py"""
import html, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = {r[0]: (r[1], r[2]) for r in (l.rstrip("\n").split("\t") for l in open(os.path.join(ROOT, "docs/img/console/manifest.tsv")))}
CAP = {
  "01-vpc-nat-gateway": "VPC → NAT gateways → rsidc-rt-nat: public NAT, EIP 47.131.152.68 (the runtime's only egress IP)",
  "02-cognito-users": "Cognito → rsidc-users → Users: 4 admin-created users, emails verified (they mirror IdC users)",
  "02b-cognito-sign-up": "Cognito → rsidc-users → Sign-up: Self-registration = Disabled (admin-only user creation)",
  "03b-idc-applications": "IAM Identity Center → Applications (AWS managed): rsidc-redshift (Redshift IdC application)",
  "03-idc-trusted-token-issuer": "IAM Identity Center → Settings → **Authentication** tab → Trusted token issuers: rsidc-cognito (click the Authentication tab; the console does not change the URL for tabs)",
  "04-redshift-cluster": "Redshift → rsidc-cluster → Properties: ra3.large, publicly addressable, IdC connection",
  "04b-redshift-security-group": "EC2 → Security group rsidc-redshift-sg: exactly 3 inbound /32 rules on 5439 (2 operator IPs + runtime NAT EIP), 0 outbound",
  "06-iam-obo-runtime-role": "IAM → rsidc-agent-runtime-role → Permissions (expanded): Bedrock, logs, workload identity, CreateTokenWithIAM on one IdC app; no redshift:*",
  "07-idc-agent-app": "IAM Identity Center → Applications → Customer managed → rsidc-data-agent: TTI authentication Configured, 4 groups assigned, trusted for AWS Redshift (1 access scope)",
  "08-agentcore-runtime-obo": "AgentCore → Runtime → rsidc_data_agent → Version 3: Inbound Auth = JWT (Cognito discovery, audience kff7mg63m7d94n6f2euip41na), VPC mode, env vars",
  "09-cognito-app-clients": "Cognito → rsidc-users → App clients: OBO client, rsidc-2lo-agent, rsidc-3lo-agent",
  "09b-cognito-domain": "Cognito → rsidc-users → Domain: rsidc-383386985941 with Managed login (v2)",
  "10-agentcore-identity": "AgentCore → Identity: Outbound Auth providers rsidc-2lo-cognito and rsidc-3lo-cognito (Custom OAuth2)",
  "10b-credential-provider-2lo": "AgentCore → Identity → rsidc-2lo-cognito: Custom OAuth2, client 3lsr6jpphlql4hb8n1ge6a8sjp, Cognito discovery URL, secret in AgentCore-managed Secrets Manager; M2M token fetches",
  "11-agentcore-gateway": "AgentCore → Gateways → rsidc-2lo-gateway: MCP gateway, IAM role rsidc-gateway-role, target 'reporting' (Lambda)",
  "11a-gateway-inbound-auth": "AgentCore → Gateways → rsidc-2lo-gateway → Inbound Auth: Cognito, Allowed clients = 3lsr6jpphlql4hb8n1ge6a8sjp (2LO client only)",
  "11b-lambda-reporting": "Lambda → rsidc-reporting → Configuration: Gateway target that queries Redshift as svc_reporting",
  "12-agentcore-runtime-oauth": "AgentCore → Runtime → rsidc_oauth_agent → Version 4: separate runtime for 2LO/3LO (JWT inbound, VPC, env CP_2LO / CP_3LO / GW_URL)",
  "12b-iam-oauth-runtime-role": "IAM → rsidc-oauth-runtime-role → oauth-runtime (expanded): GetResourceOauth2Token on token-vault + both credential providers + its workload identity; this is what authorizes the runtime to use rsidc-2lo-cognito",
}
STEPS = [  # (RUNBOOK heading prefix that starts the step section, screenshots)
  ("## Step 1:", ["01-vpc-nat-gateway"]),
  ("## Step 2:", ["02-cognito-users", "02b-cognito-sign-up"]),
  ("## Step 3:", ["03b-idc-applications", "03-idc-trusted-token-issuer"]),
  ("## Step 4:", ["04-redshift-cluster", "04b-redshift-security-group"]),
  ("## Step 6:", ["06-iam-obo-runtime-role"]),
  ("## Step 7:", ["07-idc-agent-app"]),
  ("## Step 8:", ["08-agentcore-runtime-obo"]),
  ("## Step 9:", ["09-cognito-app-clients", "09b-cognito-domain"]),
  ("## Step 10:", ["10-agentcore-identity", "10b-credential-provider-2lo"]),
  ("## Step 11:", ["11-agentcore-gateway", "11a-gateway-inbound-auth", "11b-lambda-reporting"]),
  ("## Step 12:", ["12-agentcore-runtime-oauth", "12b-iam-oauth-runtime-role"]),
]

def md_block(names):
    out = ["<!-- console-shots:start -->", "**AWS console (captured from the logged-in browser session):**", ""]
    for n in names:
        ts, url = MAN[n]
        out += [f"*{CAP[n]}*  ", f"URL at capture ({ts}): <{url}>", "", f"![{n}](docs/img/console/{n}.png)", ""]
    return "\n".join(out + ["<!-- console-shots:end -->", ""])

# ---------- RUNBOOK ----------
p = os.path.join(ROOT, "RUNBOOK.md"); s = open(p).read()
s = re.sub(r"<!-- console-shots:start -->.*?<!-- console-shots:end -->\n?", "", s, flags=re.S)
lines = s.split("\n")
for head, names in STEPS:
    i = next(k for k, l in enumerate(lines) if l.startswith(head))
    j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("## ") or lines[k].strip() == "---"), len(lines))
    lines[j:j] = md_block(names).split("\n")
open(p, "w").write("\n".join(lines))

# ---------- Email: Appendix A ----------
p = os.path.join(ROOT, "docs/email-draft.html"); e = open(p).read()
e = re.sub(r"<!-- console-appendix:start -->.*?<!-- console-appendix:end -->\n?", "", e, flags=re.S)
fig = []
for head, names in STEPS:
    step = head.replace("## ", "").rstrip(":")
    for n in names:
        ts, url = MAN[n]
        cap = html.escape(CAP[n]).replace("**", "")
        fig.append(f'<div class="avoid" style="margin:10px 0 14px"><p class="small" style="margin:0 0 2px"><b>{step} · {cap}</b><br>'
                   f'URL at capture ({html.escape(ts)}): <a href="{html.escape(url)}">{html.escape(url)}</a></p>'
                   f'<img src="img/console/{n}.png" style="width:100%;max-height:235mm;object-fit:contain;object-position:top left;border:1px solid #d5dbdb"></div>')
app = ('<!-- console-appendix:start -->\n<h2 class="pb">Appendix A. AWS console screenshots (one per setup step)</h2>\n'
       '<p class="small">Captured from my logged-in console session (account 383386985941). Each figure shows the exact URL at capture time so you can open it and validate. '
       'Steps 5 (SQL seed) and 13 (tests) have no console page; see sections 2.2 and 4.</p>\n' + "\n".join(fig) + "\n<!-- console-appendix:end -->\n")
e = e.replace("<p>Thanks,<br>", app + "\n<p>Thanks,<br>", 1)
open(p, "w").write(e)
print(f"RUNBOOK: {sum(len(n) for _, n in STEPS)} screenshots inserted across {len(STEPS)} steps; email: Appendix A")
