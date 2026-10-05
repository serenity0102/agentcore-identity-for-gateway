"""End-to-end access-control matrix: caller JWT -> AgentCore Runtime (VPC) -> Redshift as AWSIDC:<user>.
Each case states the expected outcome derived from infra/sql/01-seed-and-grants.sql."""
import os, sys, uuid
from invoke import invoke
from tokens import id_token

ALLOW, DENY = True, False
CASES = [
  # user,  description,                         sql,                                                                      expect, expect_rows
  ("wei",   "whoami",                            "SELECT current_user",                                                    ALLOW, None),
  ("wei",   "read risk",                         "SELECT * FROM risk.credit_limits",                                       ALLOW, 2),
  ("wei",   "update risk",                       "UPDATE risk.credit_limits SET risk_score=risk_score+1 WHERE customer_email='alice@cust.example'", ALLOW, None),
  ("wei",   "read sales (all regions)",          "SELECT * FROM sales.orders",                                             ALLOW, 5),
  ("wei",   "read marketing",                    "SELECT * FROM marketing.campaigns",                                      DENY,  None),
  ("zhang", "whoami",                            "SELECT current_user",                                                    ALLOW, None),
  ("zhang", "update marketing",                  "UPDATE marketing.campaigns SET budget=budget+1 WHERE campaign_id=1",     ALLOW, None),
  ("zhang", "sales non-PII cols (RLS APAC)",     "SELECT order_id, region, amount FROM sales.orders",                      ALLOW, 2),
  ("zhang", "sales PII column",                  "SELECT customer_email FROM sales.orders",                                DENY,  None),
  ("zhang", "read risk",                         "SELECT * FROM risk.credit_limits",                                       DENY,  None),
  ("chen",  "read risk",                         "SELECT * FROM risk.credit_limits",                                       ALLOW, 2),
  ("chen",  "read sales (all regions)",          "SELECT * FROM sales.orders",                                             ALLOW, 5),
  ("chen",  "update risk (read-only team)",      "UPDATE risk.credit_limits SET risk_score=0",                             DENY,  None),
  ("chen",  "privilege escalation attempt",      'GRANT SELECT ON marketing.campaigns TO ROLE "AWSIDC:data-scientists"',  DENY,  None),
  ("ds1",   "whoami (authenticated)",            "SELECT current_user",                                                    ALLOW, None),
  ("ds1",   "read sales (no grants)",            "SELECT * FROM sales.orders",                                             DENY,  None),
]

def main():
    tokens, sessions, passed = {}, {}, 0
    for user, desc, sql, expect, exp_rows in CASES:
        # One sign-in (JWT) + one runtime session per user, i.e. one conversation per user.
        tokens.setdefault(user, id_token(user))
        sessions.setdefault(user, f"rsidc-{user}-{uuid.uuid4()}")
        status, body = invoke(tokens[user], {"sql": sql}, session_id=sessions[user])
        res = body.get("result", {}) if isinstance(body, dict) else {}
        ok = res.get("ok") is True
        nrows = len(res.get("rows", [])) if ok and "rows" in res else None
        # A DENY only counts if the session was established and Redshift refused the statement itself
        # (authorization), not if the connection failed (authentication/plumbing).
        authz_denied = res.get("stage") == "execute" and "permission denied" in res.get("error", "").lower()
        good = (ok and (exp_rows is None or nrows == exp_rows)) if expect else authz_denied
        passed += good
        detail = (res.get("rows") if ok and desc.startswith("whoami") else
                  f"rows={nrows}" if nrows is not None else f"rowcount={res.get('rowcount')}" if ok else res.get("error", body))
        print(f"{'PASS' if good else 'FAIL'} | {user:5} | {desc:32} | expect={'ALLOW' if expect else 'DENY ':5} got={'ALLOW' if ok else 'DENY'} | HTTP {status} | {str(detail)[:150]}")
    print(f"\n{passed}/{len(CASES)} cases matched expectation")
    return 0 if passed == len(CASES) else 1

if __name__ == "__main__":
    sys.exit(main())
