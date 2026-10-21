"""Part 7: Entra ID x AgentCore Identity (2LO / 3LO / OBO) on runtime rsidc_entra_agent. Each phase is independent
(own runtime session, read-only downstream calls; 3LO uses its own consent session), so phases can run in parallel and
re-run for demos. Tokens, secrets and passwords are never printed.
Usage: entra_identity_tests.py <phase>    phases: 2lo | obo | 3lo        Results: tests/results/entra_identity_<phase>.json
  3lo needs a browser: the consent URL is opened with agent-browser (its own session), the user signs in, AgentCore
  redirects to http://localhost:8765/callback?session_id=..., and the test binds the session (CompleteResourceTokenAuth)."""
import base64, http.server, json, os, subprocess, sys, threading, time, urllib.parse, uuid, boto3, requests
sys.path.insert(0, os.path.dirname(__file__))
from invoke import invoke  # noqa: E402

E = os.environ
T, CLI, AGENT, D, RT = E["ENTRA_TENANT_ID"], E["ENTRA_TEST_CLIENT_ID"], E["ENTRA_AGENT_APP_ID"], E["ENTRA_DOMAIN"], E["ENTRA_RT_ARN"]
PW = dict(l.strip().split("=", 1) for l in open(os.path.join(os.path.dirname(__file__), ".entra-users.env")) if "=" in l)
TOOLS = ["mall___get_mall_list", "mall___get_footfall_summary", "mall___get_hourly_traffic", "mall___get_zone_comparison"]
USER_EXPECT = {"wei": set(TOOLS), "ds1": {"mall___get_mall_list", "mall___get_footfall_summary"}, "chen": set()}
APP_EXPECT = {"mall___get_mall_list", "mall___get_footfall_summary"}   # the AGENT app's own App Roles (2LO)
RETURN = "http://localhost:8765/callback"


def user_token(u):  # the user's Entra token FOR THE AGENT (aud = rsidc-entra-agent)
    r = requests.post(f"https://login.microsoftonline.com/{T}/oauth2/v2.0/token", timeout=30, data=dict(
        grant_type="password", client_id=CLI, username=f"{u}@{D}", password=PW[f"ENTRA_PW_{u.upper()}"],
        scope=f"api://{AGENT}/access_as_user")).json()
    if "access_token" not in r: raise RuntimeError(f"{u}: {r.get('error')} {r.get('error_description', '')[:120]}")
    return r["access_token"]


def claims(t):
    return json.loads(base64.urlsafe_b64decode(t.split(".")[1] + "=="))


def call(tok, payload):
    s, body = invoke(tok, payload, runtime_arn=RT, session_id=f"rsidc-entra-{payload['mode']}-{uuid.uuid4()}")
    return s, body if isinstance(body, dict) else {"raw": str(body)[:200]}


def main(phase):
    out = {"phase": phase, "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "runtime": RT, "cases": []}

    def rec(name, expect, actual, ev):
        ok = expect == actual
        out["cases"].append({"case": name, "expect": expect, "actual": actual, "pass": ok, "evidence": ev})
        print(f"{'PASS' if ok else 'FAIL'} {name}: expect={expect} actual={actual} | {ev}")

    if phase == "2lo":
        for u in ("wei", "ds1", "chen"):   # same answer whoever calls: the token is the AGENT's
            s, b = call(user_token(u), {"mode": "2lo"}); c = b.get("outbound_token_claims", {}); gw = b.get("gateway", {})
            rec(f"{u}: 2LO token is app-only (no user, no scp)", (None, None, AGENT), (c.get("preferred_username"), c.get("scp"), c.get("azp")), f"http={s} roles={c.get('roles')} err={b.get('error')}")
            rec(f"{u}: 2LO tools/list = the app's roles", sorted(APP_EXPECT), gw.get("listed"), f"allowed={gw.get('allowed')}")
        s, b = invoke(None, {"mode": "2lo"}, runtime_arn=RT); rec("no bearer -> runtime rejects", True, s in (401, 403), f"http={s}")
    if phase == "obo":
        for u in ("wei", "ds1", "chen"):
            t = user_token(u)
            s, b = call(t, {"mode": "obo"}); c = b.get("outbound_token_claims", {}); gw = b.get("gateway", {})
            rec(f"{u}: OBO token carries the user", f"{u}@{D}".lower(), (c.get("preferred_username") or "").lower(), f"http={s} aud={c.get('aud')} azp={c.get('azp')} roles={c.get('roles')} err={b.get('error')}")
            rec(f"{u}: OBO tools/list = the user's roles", sorted(USER_EXPECT[u]), gw.get("listed"), f"allowed={gw.get('allowed')}")
            rec(f"{u}: hidden tools denied on direct call", True, all(gw.get("allowed", {}).get(x) == (x in USER_EXPECT[u]) for x in TOOLS), f"allowed={gw.get('allowed')}")
        s, b = call(user_token("ds1"), {"mode": "obo_graph"})
        rec("ds1: OBO -> Microsoft Graph /me is ds1", f"ds1@{D}".lower(), (b.get("me", {}).get("userPrincipalName") or "").lower(), f"graph_http={b.get('graph_http')} err={b.get('error')}")
    if phase == "3lo":
        # dedicated user: interactive sign-in of wei/ds1/chen now hits the Security-defaults MFA registration (no skip left)
        u = os.environ.get("ENTRA_3LO_USER", "lo3user"); t = user_token(u)
        s, b = call(t, {"mode": "3lo", "return_url": RETURN, "force": True})
        rec("first call -> consent required", "CONSENT_REQUIRED", b.get("status"), f"http={s} has_url={bool(b.get('authorizationUrl'))} err={b.get('error')}")
        got = {}

        class CB(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                got.update(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)); self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        srv = http.server.HTTPServer(("127.0.0.1", 8765), CB); threading.Thread(target=srv.serve_forever, daemon=True).start()
        ab = ["agent-browser", "--session", "entra-3lo"]
        def visible(sel):  # wait until the Entra page has rendered the field (first browser launch is slow)
            for _ in range(30):
                r = subprocess.run(ab + ["eval", f"!!(document.querySelector('{sel}') && document.querySelector('{sel}').offsetParent)"], capture_output=True, text=True).stdout
                if "true" in r: return True
                time.sleep(1)
            return False
        # launch the browser first: launching AND navigating in one call can load the one-time request_uri twice
        # (AgentCore then answers "Invalid request")
        subprocess.run(ab + ["open", "about:blank"], capture_output=True); time.sleep(2)
        retries = 0
        for retries in range(3):  # AgentCore's hosted /authorize intermittently answers "Invalid request": ask for a fresh URL
            subprocess.run(ab + ["open", b["authorizationUrl"]], capture_output=True)
            if visible("input[name=loginfmt]"): break
            s, b = call(t, {"mode": "3lo", "return_url": RETURN, "force": True})
        out["consent_url_retries"] = retries
        subprocess.run(ab + ["fill", "input[name=loginfmt]", f"{u}@{D}"], capture_output=True); subprocess.run(ab + ["click", "input[type=submit]"], capture_output=True)
        if visible("input[name=passwd]"):
            subprocess.run(ab + ["fill", "input[name=passwd]", PW[f"ENTRA_PW_{u.upper()}"]], capture_output=True); subprocess.run(ab + ["click", "input[type=submit]"], capture_output=True)
        for _ in range(30):   # "Stay signed in?" interstitial, then AgentCore callback -> return URL
            if got: break
            txt = subprocess.run(ab + ["get", "text", "body"], capture_output=True, text=True).stdout
            if "Stay signed in" in txt: subprocess.run(ab + ["click", "#idBtn_Back"], capture_output=True)
            elif "Enter code" in txt and "authenticator" in txt.lower():   # MFA: TOTP from the registered authenticator app
                import totp
                subprocess.run(ab + ["fill", "input[name=otc]", totp.current()], capture_output=True); subprocess.run(ab + ["click", "input[type=submit]"], capture_output=True)
            elif "Skip for now" in txt: subprocess.run(ab + ["find", "text", "Skip for now", "click"], capture_output=True)
            elif "keep your account secure" in txt and "Skip" not in txt: break   # MFA registration required, no skip offered
            time.sleep(2)
        srv.shutdown()
        rec("consent completed -> AgentCore redirected to return URL", True, bool(got.get("session_id")), f"params={sorted(got)}")
        idc = boto3.Session(profile_name="default").client("bedrock-agentcore", region_name=E["RT_REGION"])
        idc.complete_resource_token_auth(sessionUri=got["session_id"][0], userIdentifier={"userToken": t})
        rec("session bound to the signed-in user (CompleteResourceTokenAuth)", True, True, "no exception")
        s, b = call(t, {"mode": "3lo", "return_url": RETURN, "session_uri": got["session_id"][0]})
        rec(f"token from vault -> Graph /me is {u}", ("TOKEN_FROM_VAULT", f"{u}@{D}".lower()), (b.get("status"), (b.get("me", {}).get("userPrincipalName") or "").lower()), f"graph_http={b.get('graph_http')} err={b.get('error')}")
        s, b = call(user_token("wei"), {"mode": "3lo", "return_url": RETURN})
        rec(f"wei (no consent of its own) does not get {u}'s token", "CONSENT_REQUIRED", b.get("status"), "vault is per (agent, user)")
    path = os.path.join(os.path.dirname(__file__), "results", f"entra_identity_{phase}.json")
    json.dump(out, open(path, "w"), indent=1)
    n = sum(c["pass"] for c in out["cases"]); print(f"\n{n}/{len(out['cases'])} PASS -> {path}")
    sys.exit(0 if n == len(out["cases"]) else 1)


if __name__ == "__main__":
    main(sys.argv[1])
