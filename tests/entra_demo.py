"""Demo helper (read-only): call runtime rsidc_entra_agent as an Entra test user and print what the agent returns
(token CLAIMS, Gateway results). Tokens are never printed.
Usage: infra/run.sh agent/.venv/bin/python tests/entra_demo.py <whoami|2lo|obo|obo_graph> <wei|ds1|chen>"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from entra_identity_tests import call, user_token  # noqa: E402

mode, user = sys.argv[1], sys.argv[2]
status, body = call(user_token(user), {"mode": mode})
print(f"HTTP {status}\n{json.dumps(body, indent=1, ensure_ascii=False)}")
