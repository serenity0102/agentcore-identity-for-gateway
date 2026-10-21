"""2LO and 3LO test cases against the separate OAuth runtime (rsidc_oauth_agent). The OBO runtime is not used here.

3LO consent is automated with agent-browser (headless Chrome) signing in to the Cognito hosted login page,
and a local callback listener on :8765 that completes AgentCore Identity session binding (CompleteResourceTokenAuth)."""
import json, os, re, subprocess, threading, time, urllib.parse, urllib.request, uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

import boto3
from invoke import invoke
from tokens import id_token, load_pw

RT = os.environ["OAUTH_RT_ARN"]; RETURN_URL = "http://localhost:8765/callback"
ident = boto3.Session().client("bedrock-agentcore", region_name=os.environ["RT_REGION"])
results = []


def record(case, expect, got, ok, detail, observe=False):
    """observe=True: documented service behaviour, printed as OBSERVED and not counted as pass/fail."""
    if not observe: results.append(ok)
    tag = "OBSERVED" if observe else ("PASS" if ok else "FAIL")
    print(f"{tag:8} | {case:58} | expect={expect:22} got={got:22} | {str(detail)[:170]}")


# ---------- local OAuth return-URL listener (stands in for the app's callback page) ----------
class Cb(BaseHTTPRequestHandler):
    hits = []
    def do_GET(self):
        Cb.hits.append(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query))
        self.send_response(200); self.end_headers(); self.wfile.write(b"consent received - you can close this tab")
    def log_message(self, *a): pass

srv = HTTPServer(("127.0.0.1", 8765), Cb); threading.Thread(target=srv.serve_forever, daemon=True).start()


def ab(browser, *args):
    return subprocess.run(["agent-browser", "--session", browser, *args], capture_output=True, text=True, timeout=60).stdout


def browser_consent(auth_url, login_as, browser):
    """Simulate the human in browser profile `browser`: open the auth URL; if Cognito shows the login form, sign in
    as `login_as` (if the browser already has a Cognito session, Cognito silently reuses it); wait for RETURN_URL."""
    n = len(Cb.hits)
    ab(browser, "open", auth_url)
    for _ in range(20):  # wait until the IdP login form renders, or the IdP silently redirects back (existing session)
        if len(Cb.hits) > n: return Cb.hits[-1] | {"_login_form": False}
        snap = ab(browser, "snapshot")
        m = lambda label: re.search(rf'{label}.*?\[.*?ref=(e\d+)\]', snap)
        if m('textbox "Username"') and m('textbox "Password"'): break
        time.sleep(1)
    else:
        return {"_timeout": ab(browser, "get", "url")}
    ab(browser, "fill", "@" + m('textbox "Username"').group(1), login_as)
    ab(browser, "fill", "@" + m('textbox "Password"').group(1), load_pw(login_as))
    ab(browser, "click", "@" + m('button "(?:submit|Sign in)"').group(1))
    for _ in range(30):
        if len(Cb.hits) > n: return Cb.hits[-1] | {"_login_form": True}
        time.sleep(1)
    return {"_timeout": ab(browser, "get", "url")}


def call(user_tok, payload):
    return invoke(user_tok, payload, runtime_arn=RT, session_id=f"rsidc-oauth-{uuid.uuid4()}")[1]


def complete(session_uri, user_tok):
    try:
        ident.complete_resource_token_auth(sessionUri=session_uri, userIdentifier={"userToken": user_tok})
        return "OK"
    except Exception as e:
        return f"{type(e).__name__}: {str(e)[:120]}"


idp = boto3.Session().client("cognito-idp", region_name=os.environ["RT_REGION"])
TEMP = {}


def temp_user(tag):
    """Admin-created throwaway user (empty Token Vault slot every run). Deleted at the end of the run."""
    name = f"tmp-{tag}-{uuid.uuid4().hex[:6]}"; pw = f"Tp{uuid.uuid4().hex[:12]}Aa1"
    idp.admin_create_user(UserPoolId=os.environ["COGNITO_POOL_ID"], Username=name, MessageAction="SUPPRESS",
                          UserAttributes=[{"Name": "email", "Value": f"{name}@test.example"}, {"Name": "email_verified", "Value": "true"}])
    idp.admin_set_user_password(UserPoolId=os.environ["COGNITO_POOL_ID"], Username=name, Password=pw, Permanent=True)
    t = idp.initiate_auth(ClientId=os.environ["COGNITO_CLIENT_ID"], AuthFlow="USER_PASSWORD_AUTH",
                          AuthParameters={"USERNAME": name, "PASSWORD": pw})["AuthenticationResult"]["IdToken"]
    TEMP[name] = pw
    return name, t


_load_pw = load_pw
def load_pw(user):  # noqa: F811 - temp users' passwords live in memory only
    return TEMP.get(user) or _load_pw(user)


tok = {u: id_token(u) for u in ("wei", "zhang", "ds1")}

print("=== 2LO (M2M): agent acts as ITSELF via Credential Provider -> AgentCore Gateway -> Lambda -> Redshift svc_reporting")
for u in ("wei", "zhang", "ds1"):
    b = call(tok[u], {"mode": "2lo"})
    rows = b.get("gateway_result", {}).get("rows", [])
    users = {r[0] for r in rows}; pii = any("@" in str(r[3]) for r in rows)
    record(f"2LO as {u}: report via Gateway", "5 rows, svc_reporting", f"{len(rows)} rows, {','.join(users)}",
           len(rows) == 5 and users == {"svc_reporting"} and pii,
           f"token sub={b.get('outbound_token_claims',{}).get('sub')} scope={b.get('outbound_token_claims',{}).get('scope')} PII visible={pii}")

gw = os.environ["GW_URL"]; body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
for label, t in (("no token", None), ("wei's USER id token (not the 2LO client)", tok["wei"])):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if t: h["Authorization"] = f"Bearer {t}"
    try:
        code = urllib.request.urlopen(urllib.request.Request(gw, data=body, headers=h), timeout=20).status
    except urllib.error.HTTPError as e:
        code = e.code
    record(f"2LO Gateway called directly with {label}", "401/403", str(code), code in (401, 403), "Gateway inbound JWT authorizer (allowedClients = 2LO client only)")

print("\n=== 3LO (USER_FEDERATION): user consents once; token stored in Token Vault per (agent, user)")
b = call(tok["wei"], {"mode": "3lo", "return_url": RETURN_URL, "force": True})
record("3LO wei first call", "CONSENT_REQUIRED", b.get("status", b.get("error")), b.get("status") == "CONSENT_REQUIRED", b.get("authorizationUrl", "")[:110])
cb = browser_consent(b["authorizationUrl"], "wei", "rsidc-wei")
record("3LO wei signs in at Cognito -> redirected to app return URL", "callback", "callback" if "_timeout" not in cb else "timeout", "_timeout" not in cb, cb)
r = complete(b["sessionUri"], tok["wei"])
record("3LO CompleteResourceTokenAuth (session binding) with wei's JWT", "OK", r[:22], r == "OK", r)
b2 = call(tok["wei"], {"mode": "3lo", "return_url": RETURN_URL})
ui = b2.get("userinfo", {})
record("3LO wei second call (new runtime session)", "TOKEN_FROM_VAULT", b2.get("status", b2.get("error")),
       b2.get("status") == "TOKEN_FROM_VAULT" and ui.get("username") == "wei", f"userinfo username={ui.get('username')} email={ui.get('email')} claims={b2.get('outbound_token_claims')}")

z = call(tok["zhang"], {"mode": "3lo", "return_url": RETURN_URL, "force": True})
record("3LO zhang call: wei's vault token must NOT be reused", "CONSENT_REQUIRED", z.get("status", z.get("error")), z.get("status") == "CONSENT_REQUIRED", "vault is keyed by (agent, user)")
cbz = browser_consent(z["authorizationUrl"], "zhang", "rsidc-zhang")
r = complete(z["sessionUri"], tok["wei"])
record("3LO session binding: zhang's session completed with WEI's JWT", "rejected", "OK" if r == "OK" else "rejected", r != "OK", r)
r = complete(z["sessionUri"], tok["zhang"])
record("3LO session binding: zhang's session completed with zhang's JWT", "OK", r[:22], r == "OK", r)
z2 = call(tok["zhang"], {"mode": "3lo", "return_url": RETURN_URL})
record("3LO zhang second call", "TOKEN_FROM_VAULT (zhang)", f"{z2.get('status')} ({z2.get('userinfo',{}).get('username')})",
       z2.get("status") == "TOKEN_FROM_VAULT" and z2.get("userinfo", {}).get("username") == "zhang", z2.get("userinfo"))
w3 = call(tok["wei"], {"mode": "3lo", "return_url": RETURN_URL})
record("3LO wei still gets wei's own token (no cross-user overwrite)", "TOKEN_FROM_VAULT (wei)", f"{w3.get('status')} ({w3.get('userinfo',{}).get('username')})",
       w3.get("userinfo", {}).get("username") == "wei", w3.get("userinfo"))

print("\n=== 3LO risk scenario: shared browser. A's auth URL is opened in a browser already signed in to Cognito as wei")
a_name, a_tok = temp_user("a")
d = call(a_tok, {"mode": "3lo", "return_url": RETURN_URL})
cbr = browser_consent(d["authorizationUrl"], a_name, "rsidc-wei")   # Cognito SSO silently reuses wei's session
r = complete(d["sessionUri"], a_tok)                                # the app correctly binds the session to A
d2 = call(a_tok, {"mode": "3lo", "return_url": RETURN_URL})
record("3LO shared browser: wei's IdP session consents for A -> agent guard", "IDENTITY_MISMATCH", f"{d2.get('status')}",
       d2.get("status") == "IDENTITY_MISMATCH" and cbr.get("_login_form") is False,
       f"login form shown={cbr.get('_login_form')}; complete={r}; caller={d2.get('caller_email')} vault token={d2.get('vault_token_email')}")
d = call(a_tok, {"mode": "3lo", "return_url": RETURN_URL, "force": True})
cbf = browser_consent(d["authorizationUrl"], a_name, f"rsidc-clean-{a_name}")   # clean browser: A really signs in as A
r = complete(d["sessionUri"], a_tok)
d4 = call(a_tok, {"mode": "3lo", "return_url": RETURN_URL, "session_uri": d["sessionUri"]})
record("3LO recovery: forced re-consent by A in a clean browser", "TOKEN_FROM_VAULT (A)",
       f"{d4.get('status')} ({d4.get('userinfo',{}).get('username')})",
       d4.get("status") == "TOKEN_FROM_VAULT" and d4.get("userinfo", {}).get("username") == a_name,
       f"login form shown={cbf.get('_login_form')}; complete={r}; stale wei token replaced by A's own token")

print("\n=== 3LO mitigation attempt: B's consent requested with prompt=login, in the browser signed in as wei")
b_name, b_tok = temp_user("b")
d = call(b_tok, {"mode": "3lo", "return_url": RETURN_URL, "prompt_login": True})
cbm = browser_consent(d["authorizationUrl"], b_name, "rsidc-wei")
record("3LO prompt=login forces the IdP login form despite wei's session", "login form shown", str(cbm.get("_login_form")),
       cbm.get("_login_form") is True, "Cognito managed login v2 honours prompt=login (v1 classic hosted UI ignores it)")
r = complete(d["sessionUri"], b_tok)
d3 = call(b_tok, {"mode": "3lo", "return_url": RETURN_URL, "session_uri": d["sessionUri"]})
record("3LO token stored after a prompt=login consent?", "TOKEN_FROM_VAULT (B)", f"{d3.get('status')}", d3.get("status") == "TOKEN_FROM_VAULT",
       f"complete={r}; same flow without prompt=login stores the token (see wei/zhang cases)", observe=True)
c_name, c_tok = temp_user("c")
d = call(c_tok, {"mode": "3lo", "return_url": RETURN_URL})
browser_consent(d["authorizationUrl"], c_name, f"rsidc-clean-{c_name}")
r = complete(d["sessionUri"], c_tok)
d5 = call(c_tok, {"mode": "3lo", "return_url": RETURN_URL})
record("3LO control: fresh user C, no prompt=login, clean browser", "TOKEN_FROM_VAULT (C)", f"{d5.get('status')}",
       d5.get("status") == "TOKEN_FROM_VAULT" and d5.get("userinfo", {}).get("username") == c_name, f"complete={r}")

for n in TEMP:
    idp.admin_delete_user(UserPoolId=os.environ["COGNITO_POOL_ID"], Username=n)
    ab(f"rsidc-clean-{n}", "close")
srv.shutdown()
for br in ("rsidc-wei", "rsidc-zhang"): ab(br, "close")
print(f"\n{sum(results)}/{len(results)} asserted 2LO/3LO cases matched expectation (OBSERVED rows are documented behaviour)")
