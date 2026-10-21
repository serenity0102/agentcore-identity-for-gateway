"""Part 4 (customer version): per-user tool RBAC for the customer's 4 mall tools behind AgentCore Gateway (the MCP server
Amazon Quick connects to). Tokens are minted for the Quick app client rsidc-quick-mcp (same client, same trigger, same
claims as Quick's authorization-code tokens) via ADMIN_USER_PASSWORD_AUTH. Tokens and secrets are never printed.
Usage: mall_rbac_tests.py <phase>   phases: log_only | enforce | change
Results: tests/results/mall_<phase>.json"""
import base64, hashlib, hmac, json, os, sys, time, boto3, requests
sys.path.insert(0, os.path.dirname(__file__))
from tokens import load_pw, access_token as obo_access_token, id_token  # noqa: E402

R, POOL, GW = os.environ["RT_REGION"], os.environ["COGNITO_POOL_ID"], os.environ["MALL_GW_URL"]
S = boto3.Session(profile_name="default"); idp = S.client("cognito-idp", region_name=R)
TOOLS = ["mall___get_mall_list", "mall___get_footfall_summary", "mall___get_hourly_traffic", "mall___get_zone_comparison"]
ROLE = {"mall___get_mall_list": "Tools.Mall.List", "mall___get_footfall_summary": "Tools.Mall.Footfall",
        "mall___get_hourly_traffic": "Tools.Mall.Hourly", "mall___get_zone_comparison": "Tools.Mall.Zone"}
EXPECT = {"wei": set(TOOLS), "ds1": {"mall___get_mall_list", "mall___get_footfall_summary"}, "chen": set()}
VIEWER_DESC = "[rsidc-rbac] tools=Tools.Mall.List,Tools.Mall.Footfall"


def quick_client():
    env = dict(l.strip().split("=", 1) for l in open(os.path.join(os.path.dirname(__file__), ".quick-client.env")) if "=" in l)
    return env["QUICK_CLIENT_ID"], env["QUICK_CLIENT_SECRET"]


def quick_auth(user, refresh=None):
    cid, sec = quick_client()
    sh = base64.b64encode(hmac.new(sec.encode(), (user + cid).encode(), hashlib.sha256).digest()).decode()
    if refresh:
        p = dict(AuthFlow="REFRESH_TOKEN_AUTH", AuthParameters={"REFRESH_TOKEN": refresh, "SECRET_HASH": sh})
    else:
        p = dict(AuthFlow="ADMIN_USER_PASSWORD_AUTH", AuthParameters={"USERNAME": user, "PASSWORD": load_pw(user), "SECRET_HASH": sh})
    return idp.admin_initiate_auth(UserPoolId=POOL, ClientId=cid, **p)["AuthenticationResult"]


def claims(t):
    return json.loads(base64.urlsafe_b64decode(t.split(".")[1] + "=="))


def rpc(token, method, params=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method, **({"params": params} if params is not None else {})}
    r = requests.post(GW, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                                   "Accept": "application/json, text/event-stream"}, json=body, timeout=60)
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
    c = json.loads(base64.urlsafe_b64decode(p + "==")); c["roles"] = list(ROLE.values())
    return f"{h}.{base64.urlsafe_b64encode(json.dumps(c).encode()).decode().rstrip('=')}.{sig}"


def m2m_token():  # 2LO agent token via AgentCore Identity (test workload identity from Part 3)
    ac = S.client("bedrock-agentcore", region_name=R)
    wat = ac.get_workload_access_token(workloadName=os.environ["RBAC_TEST_WI"])["workloadAccessToken"]
    return ac.get_resource_oauth2_token(workloadIdentityToken=wat, resourceCredentialProviderName="rsidc-2lo-cognito",
                                        scopes=["rsidc-reports/read"], oauth2Flow="M2M")["accessToken"]


def main(phase):
    out = {"phase": phase, "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "gateway": GW, "cases": []}

    def rec(name, expect, actual, ev):
        ok = expect == actual
        out["cases"].append({"case": name, "expect": expect, "actual": actual, "pass": ok, "evidence": ev})
        print(f"{'PASS' if ok else 'FAIL'} {name}: expect={expect} actual={actual} | {ev}")

    if phase in ("log_only", "enforce"):
        enforce = phase == "enforce"
        for u in ("wei", "ds1", "chen"):
            t = quick_auth(u)["AccessToken"]; c = claims(t)
            exp = EXPECT[u] if enforce else set(TOOLS)
            s, names = listed(t)
            rec(f"{u} tools/list (Quick client)", sorted(exp), names, f"http={s} roles={c.get('roles')} client_id={c['client_id']}")
            for tool in TOOLS:
                ok, s, d = call(t, tool)
                rec(f"{u} tools/call {tool.split('___')[1]}", (tool in exp), ok, f"http={s} {d}")
        if enforce:
            s, names = listed(obo_access_token("wei"))
            rec("wei tools/list (OBO client, same roles)", sorted(TOOLS), names, f"http={s}")
            t = quick_auth("ds1")["AccessToken"]
            s, j = rpc(tamper(t), "tools/list"); rec("tampered ds1 token (roles forged to all 4)", 403, s, "signature check")
            s, j = rpc(m2m_token(), "tools/list"); rec("2LO M2M token (client not allowed)", 403, s, "allowedClients")
            s, j = rpc(id_token("wei"), "tools/list"); rec("ID token instead of access token", 403, s, "token_use")
            s, j = rpc("not-a-jwt", "tools/list"); rec("garbage bearer", 401, s, "")
            lam = S.client("lambda", region_name=R)
            for api, kw in (("get_policy", {}), ("get_function_url_config", {})):
                try:
                    getattr(lam, api)(FunctionName="rsidc-mall-tools", **kw); got = "present"
                except lam.exceptions.ResourceNotFoundException:
                    got = "none"
                rec(f"bypass: Lambda {api.split('get_')[1]}", "none", got, "no public path around the Gateway")
            iam = S.client("iam"); fn = f"arn:aws:lambda:{R}:{os.environ['ACCOUNT_ID']}:function:rsidc-mall-tools"
            for role, exp in (("rsidc-mall-gateway-role", "allowed"), ("rsidc-webchat-role", "implicitDeny"), ("rsidc-oauth-runtime-role", "implicitDeny")):
                d = iam.simulate_principal_policy(PolicySourceArn=f"arn:aws:iam::{os.environ['ACCOUNT_ID']}:role/{role}",
                                                  ActionNames=["lambda:InvokeFunction"], ResourceArns=[fn])["EvaluationResults"][0]["EvalDecision"]
                rec(f"bypass: {role} -> lambda:InvokeFunction", exp, d, "IAM policy simulation")
    if phase == "change":  # only the Cognito group Description changes; Cedar / Lambda / Gateway untouched
        a = quick_auth("ds1"); old = a["AccessToken"]
        ok, s, d = call(old, "mall___get_hourly_traffic"); rec("before: ds1 hourly", False, ok, f"roles={claims(old).get('roles')}")
        idp.update_group(UserPoolId=POOL, GroupName="mall-viewer", Description=VIEWER_DESC + ",Tools.Mall.Hourly")
        t0 = time.time()
        try:
            new = quick_auth("ds1")["AccessToken"]
            ok, s, d = call(new, "mall___get_hourly_traffic"); rec("after edit, new sign-in: ds1 hourly", True, ok, f"roles={claims(new).get('roles')} {time.time()-t0:.1f}s after edit")
            ok, s, d = call(old, "mall___get_hourly_traffic"); rec("after edit, OLD token: ds1 hourly", False, ok, "claims frozen in the old token until it expires")
            ref = quick_auth("ds1", refresh=a["RefreshToken"])["AccessToken"]
            ok, s, d = call(ref, "mall___get_hourly_traffic"); rec("after edit, REFRESH token (what Quick does): ds1 hourly", True, ok, f"roles={claims(ref).get('roles')}")
        finally:
            idp.update_group(UserPoolId=POOL, GroupName="mall-viewer", Description=VIEWER_DESC)
        new = quick_auth("ds1")["AccessToken"]
        ok, s, d = call(new, "mall___get_hourly_traffic"); rec("restored: ds1 hourly", False, ok, f"roles={claims(new).get('roles')}")
    passed = sum(c["pass"] for c in out["cases"]); out["summary"] = f"{passed}/{len(out['cases'])} passed"
    print(out["summary"])
    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "results", f"mall_{phase}.json"), "w"), indent=1)
    sys.exit(0 if passed == len(out["cases"]) else 1)


if __name__ == "__main__":
    main(sys.argv[1])
