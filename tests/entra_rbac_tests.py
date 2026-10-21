"""Part 6 (Entra ID version): per-user tool RBAC on rsidc-mall-entra-gateway. Entra access tokens (v2, aud = rsidc-mall-api)
carry the App Role claim `roles` natively; the Gateway's Cedar rules match it. Tokens via ROPC on the public test client
(fine for test users without MFA). Tokens and passwords are never printed.
Usage: entra_rbac_tests.py <phase>   phases: log_only | enforce | change     Results: tests/results/entra_<phase>.json"""
import base64, json, os, subprocess, sys, time, requests
sys.path.insert(0, os.path.dirname(__file__))
from tokens import access_token as cognito_access_token  # noqa: E402

T, API, CLI, D, GW = (os.environ[k] for k in ("ENTRA_TENANT_ID", "ENTRA_API_APP_ID", "ENTRA_TEST_CLIENT_ID", "ENTRA_DOMAIN", "ENTRA_GW_URL"))
PW = dict(l.strip().split("=", 1) for l in open(os.path.join(os.path.dirname(__file__), ".entra-users.env")) if "=" in l)
TOOLS = ["mall___get_mall_list", "mall___get_footfall_summary", "mall___get_hourly_traffic", "mall___get_zone_comparison"]
EXPECT = {"wei": set(TOOLS), "ds1": {"mall___get_mall_list", "mall___get_footfall_summary"}, "chen": set()}


def entra_token(user, scope=None):
    r = requests.post(f"https://login.microsoftonline.com/{T}/oauth2/v2.0/token", timeout=30, data=dict(
        grant_type="password", client_id=CLI, username=f"{user}@{D}", password=PW[f"ENTRA_PW_{user.upper()}"],
        scope=scope or f"api://{API}/mcp.access")).json()
    return r["access_token"]


def claims(t):
    return json.loads(base64.urlsafe_b64decode(t.split(".")[1] + "=="))


def rpc(token, method, params=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method, **({"params": params} if params is not None else {})}
    r = requests.post(GW, json=body, timeout=60, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                                                       "Accept": "application/json, text/event-stream"})
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"raw": r.text[:200]}


def listed(token):
    s, j = rpc(token, "tools/list")
    return s, sorted(t["name"] for t in j.get("result", {}).get("tools", []))


def call(token, name):
    s, j = rpc(token, "tools/call", {"name": name, "arguments": {"mall_id": "HK01", "date": "2026-10-01"}})
    res = j.get("result", {})
    ok = s == 200 and "error" not in j and not res.get("isError")
    txt = (j.get("error") or {}).get("message") or (res.get("content") or [{}])[0].get("text", "")
    return ok, s, txt[:110].replace("\n", " ")


def tamper(token):
    h, p, sig = token.split(".")
    c = json.loads(base64.urlsafe_b64decode(p + "==")); c["roles"] = ["Tools.Mall.List", "Tools.Mall.Footfall", "Tools.Mall.Hourly", "Tools.Mall.Zone"]
    return f"{h}.{base64.urlsafe_b64encode(json.dumps(c).encode()).decode().rstrip('=')}.{sig}"


def graph(method, path, body=None):  # admin changes in the Entra tenant (az login session)
    tok = json.loads(subprocess.check_output(["az", "account", "get-access-token", "--resource-type", "ms-graph", "--tenant", T]))["accessToken"]
    r = requests.request(method, "https://graph.microsoft.com/v1.0" + path, json=body, timeout=30,
                         headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    r.raise_for_status(); return r.json() if r.text else {}


def main(phase):
    out = {"phase": phase, "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "gateway": GW, "cases": []}

    def rec(name, expect, actual, ev):
        ok = expect == actual
        out["cases"].append({"case": name, "expect": expect, "actual": actual, "pass": ok, "evidence": ev})
        print(f"{'PASS' if ok else 'FAIL'} {name}: expect={expect} actual={actual} | {ev}")

    if phase in ("log_only", "enforce"):
        enforce = phase == "enforce"
        for u in ("wei", "ds1", "chen"):
            t = entra_token(u); c = claims(t)
            exp = EXPECT[u] if enforce else set(TOOLS)
            s, names = listed(t)
            rec(f"{u} tools/list", sorted(exp), names, f"http={s} ver={c.get('ver')} roles={c.get('roles')}")
            for tool in TOOLS:
                ok, s, d = call(t, tool)
                rec(f"{u} tools/call {tool.split('___')[1]}", tool in exp, ok, f"http={s} {d}")
        if enforce:
            s, _ = rpc(tamper(entra_token("ds1")), "tools/list"); rec("tampered ds1 token (roles forged to all 4)", 403, s, "signature check")
            s, _ = rpc(cognito_access_token("wei"), "tools/list"); rec("Cognito access token (other issuer)", 403, s, "issuer/JWKS")
            g = entra_token("wei", "https://graph.microsoft.com/.default")
            s, _ = rpc(g, "tools/list"); rec("Entra token for Microsoft Graph (wrong audience)", True, s in (401, 403), f"http={s} aud={claims(g).get('aud')}")
            s, _ = rpc("not-a-jwt", "tools/list"); rec("garbage bearer", 401, s, "")
    if phase == "change":  # only the Entra App Role assignment changes; Cedar / Lambda / Gateway untouched
        sp = graph("GET", f"/servicePrincipals?$filter=appId eq '{API}'")["value"][0]
        role = next(r["id"] for r in sp["appRoles"] if r["value"] == "Tools.Mall.Hourly")
        uid = graph("GET", f"/users/ds1@{D}")["id"]
        old = entra_token("ds1"); ok, s, d = call(old, "mall___get_hourly_traffic"); rec("before: ds1 hourly", False, ok, f"roles={claims(old).get('roles')}")
        a = graph("POST", f"/servicePrincipals/{sp['id']}/appRoleAssignedTo", {"principalId": uid, "resourceId": sp["id"], "appRoleId": role})
        try:
            t0 = time.time(); new = None
            for _ in range(12):  # Entra directory replication: poll until a fresh token carries the role
                new = entra_token("ds1")
                if "Tools.Mall.Hourly" in (claims(new).get("roles") or []): break
                time.sleep(10)
            ok, s, d = call(new, "mall___get_hourly_traffic")
            rec("after assignment, new token: ds1 hourly", True, ok, f"roles={claims(new).get('roles')} {time.time()-t0:.0f}s after assignment")
            ok, s, d = call(old, "mall___get_hourly_traffic"); rec("after assignment, OLD token: ds1 hourly", False, ok, "claims frozen until the old token expires")
        finally:
            graph("DELETE", f"/servicePrincipals/{sp['id']}/appRoleAssignedTo/{a['id']}")
        rec("restore: Hourly assignment removed", True, True, "appRoleAssignment deleted")
    path = os.path.join(os.path.dirname(__file__), "results", f"entra_{phase}.json")
    json.dump(out, open(path, "w"), indent=1)
    n = sum(c["pass"] for c in out["cases"]); print(f"\n{n}/{len(out['cases'])} PASS -> {path}")
    sys.exit(0 if n == len(out["cases"]) else 1)


if __name__ == "__main__":
    main(sys.argv[1])
