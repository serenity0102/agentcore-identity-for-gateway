"""Part 3: per-user tool RBAC on AgentCore Gateway (Policy in AgentCore / Cedar on an Entra-style `roles` claim).
Calls the RBAC gateway's MCP endpoint directly with each persona's Cognito ACCESS token.
Usage: rbac_tests.py <phase>   phases: baseline | log_only | enforce | probe (prints only, no asserts)
Results are written to tests/results/rbac_<phase>.json. Tokens are never printed."""
import base64, json, os, sys, time, boto3, requests
sys.path.insert(0, os.path.dirname(__file__))
from tokens import access_token  # noqa: E402

GW = os.environ["RBAC_GW_URL"]; A, B = "sales___get_sales_summary", "crm___get_customer_contacts"


def rpc(token, method, params=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method, **({"params": params} if params is not None else {})}
    r = requests.post(GW, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                                   "Accept": "application/json, text/event-stream"}, json=body, timeout=60)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"raw": r.text[:300]}


def tool_names(token):
    s, j = rpc(token, "tools/list")
    return s, sorted(t["name"] for t in j.get("result", {}).get("tools", [])), j


def call(token, name):
    s, j = rpc(token, "tools/call", {"name": name, "arguments": {}})
    res = j.get("result", {})
    ok = s == 200 and "error" not in j and not res.get("isError")
    detail = (j.get("error") or {}).get("message") or (res.get("content") or [{}])[0].get("text", "")[:160]
    return ok, s, detail


def tamper(token):  # re-encode the payload with extra roles; the signature no longer matches
    h, p, sig = token.split(".")
    c = json.loads(base64.urlsafe_b64decode(p + "=="))
    c["roles"] = ["Tools.Sales.Read", "Tools.CRM.Read"]
    return f"{h}.{base64.urlsafe_b64encode(json.dumps(c).encode()).decode().rstrip('=')}.{sig}"


def m2m_token():  # the 2LO agent's own token, fetched the same way the agent does (AgentCore Identity, M2M flow)
    ac = boto3.Session().client("bedrock-agentcore", region_name=os.environ["RT_REGION"])
    # The runtime's workload identity is service-linked (callers can't use it), so a standalone test identity is used.
    wat = ac.get_workload_access_token(workloadName=os.environ["RBAC_TEST_WI"])["workloadAccessToken"]
    return ac.get_resource_oauth2_token(workloadIdentityToken=wat, resourceCredentialProviderName="rsidc-2lo-cognito",
                                        scopes=["rsidc-reports/read"], oauth2Flow="M2M")["accessToken"]


def main(phase):
    out, checks = {"phase": phase, "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "cases": []}, []

    def record(name, expect, actual, evidence):
        ok = (expect == actual) if (expect is not None and phase != "probe") else None
        out["cases"].append({"case": name, "expect": expect, "actual": actual, "pass": ok, "evidence": evidence})
        checks.append(ok)
        print(f"{'PASS' if ok else ('INFO' if ok is None else 'FAIL'):4} {name}: expect={expect} actual={actual} | {evidence}")

    tok = {u: access_token(u) for u in ("wei", "ds1", "chen")}
    enforce = phase in ("enforce", "probe")
    for u, allowed in (("wei", {A, B}), ("ds1", {A}), ("chen", set())):
        s, names, _ = tool_names(tok[u])
        record(f"{u} tools/list", sorted(allowed) if enforce else sorted({A, B}), names, f"http={s}")
        for t in (A, B):
            ok, s, d = call(tok[u], t)
            record(f"{u} tools/call {t.split('___')[1]}", (t in allowed) if enforce else True, ok, f"http={s} {d}")
    if phase != "baseline":
        # Observed: the gateway answers a well-formed JWT that fails signature/client checks with 403 insufficient_scope,
        # and only an unparseable bearer with 401 invalid_token. Either way no tool is listed.
        s, j = rpc(tamper(tok["ds1"]), "tools/list")
        record("ds1 tampered token (roles + Tools.CRM.Read)", 403, s, str(j)[:120])
        s, j = rpc("not-a-jwt", "tools/list")
        record("garbage bearer", 401, s, str(j)[:120])
        s, j = rpc(m2m_token(), "tools/list")
        record("2LO M2M token (client not allowed)", 403, s, str(j)[:120])
    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    with open(os.path.join(os.path.dirname(__file__), "results", f"rbac_{phase}.json"), "w") as f:
        json.dump(out, f, indent=1)
    asserted = [c for c in checks if c is not None]
    print(f"{phase}: {sum(asserted)}/{len(asserted)} asserted checks passed")
    return 0 if all(asserted) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "probe"))
