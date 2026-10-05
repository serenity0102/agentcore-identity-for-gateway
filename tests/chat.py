"""Talk to the OBO data agent as an end user.
  infra/run.sh agent/.venv/bin/python tests/chat.py <user> ["question"]     (no question = interactive)
Signs in to Cognito with the user's password (tests/.users.env), then invokes the AgentCore Runtime with the
ID token as a bearer token. One runtime session per chat, so the IdC token exchange happens once."""
import os, sys, uuid
sys.path.insert(0, os.path.dirname(__file__))
from invoke import invoke
from tokens import id_token

user = sys.argv[1] if len(sys.argv) > 1 else "wei"
tok, sid = id_token(user), f"rsidc-chat-{user}-{uuid.uuid4()}"
print(f"signed in as {user}; session {sid}")
qs = [" ".join(sys.argv[2:])] if len(sys.argv) > 2 else iter(lambda: input(f"{user}> "), "exit")
for q in qs:
    if not q.strip(): continue
    status, body = invoke(tok, {"prompt": q}, session_id=sid)
    print(body.get("answer", body) if isinstance(body, dict) else body, "\n")
