"""Part 3, tests 7-8: change ONLY IAM Identity Center (no Cedar / Lambda / Gateway change) and observe the effect.
7: remove tool A from the rsidc-gw-viewer group's Description -> ds1's NEW token has no roles -> A disappears; restore.
8: add ds1 to rsidc-gw-analyst -> ds1's NEW token gets Tools.CRM.Read -> B appears; remove the membership again.
Also records what an ALREADY-ISSUED token still allows (changes apply at the next token issuance)."""
import base64, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from tokens import access_token  # noqa: E402
import rbac_tests as T  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), ".."); IDC = ["aws", "--region", os.environ["IDC_REGION"], "identitystore"]
S = os.environ["IDENTITY_STORE_ID"]; results, ok_all = [], True


def roles(tok):
    return json.loads(base64.urlsafe_b64decode(tok.split(".")[1] + "==")).get("roles")


def check(name, expect, actual, evidence=""):
    global ok_all
    ok = expect == actual; ok_all &= ok
    results.append({"case": name, "expect": expect, "actual": actual, "pass": ok, "evidence": evidence})
    print(f"{'PASS' if ok else 'FAIL'} {name}: expect={expect} actual={actual} {evidence}")


def sh(*a):
    return subprocess.run(list(a), check=True, capture_output=True, text=True).stdout.strip()


def gid(name):
    return sh(*IDC, "list-groups", "--identity-store-id", S, "--filters", f"AttributePath=DisplayName,AttributeValue={name}",
              "--query", "Groups[0].GroupId", "--output", "text")


# --- 7: edit the mapping only
old = access_token("ds1")
sh("bash", f"{ROOT}/infra/15-rbac-idc-groups.sh", "set-viewer-tools", "")
t0 = time.time(); new = access_token("ds1")
check("7 new token roles after removing A from rsidc-gw-viewer", [], roles(new), f"(token issued {time.time()-t0:.1f}s after the IdC change)")
check("7 new token tools/list", [], T.tool_names(new)[1])
check("7 new token call A", False, T.call(new, T.A)[0])
check("7 OLD token (issued before the change) still calls A", True, T.call(old, T.A)[0], "-> takes effect only at next token issuance")
sh("bash", f"{ROOT}/infra/15-rbac-idc-groups.sh", "set-viewer-tools", "Tools.Sales.Read")
check("7 restored: tools/list", [T.A], T.tool_names(access_token("ds1"))[1])

# --- 8: change membership only
uid = sh(*IDC, "get-user-id", "--identity-store-id", S, "--alternate-identifier",
         json.dumps({"UniqueAttribute": {"AttributePath": "emails.value", "AttributeValue": "tojackywu@gmail.com"}}), "--query", "UserId", "--output", "text")
mid = sh(*IDC, "create-group-membership", "--identity-store-id", S, "--group-id", gid("rsidc-gw-analyst"),
         "--member-id", f"UserId={uid}", "--query", "MembershipId", "--output", "text")
try:
    new = access_token("ds1")
    check("8 ds1 added to rsidc-gw-analyst: roles", ["Tools.CRM.Read", "Tools.Sales.Read"], roles(new))
    check("8 tools/list", sorted([T.A, T.B]), T.tool_names(new)[1])
    check("8 call B", True, T.call(new, T.B)[0])
finally:
    sh(*IDC, "delete-group-membership", "--identity-store-id", S, "--membership-id", mid)  # only the membership this test created
new = access_token("ds1")
check("8 membership removed: tools/list", [T.A], T.tool_names(new)[1])
check("8 membership removed: call B", False, T.call(new, T.B)[0])

json.dump(results, open(os.path.join(os.path.dirname(__file__), "results", "rbac_changes.json"), "w"), indent=1)
print(f"changes: {sum(r['pass'] for r in results)}/{len(results)} passed"); sys.exit(0 if ok_all else 1)
