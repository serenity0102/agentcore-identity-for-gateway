"""Local web chat for the OBO data agent: sign in on Cognito managed login (auth code + PKCE), then chat.
The ID token stays server-side (in memory, keyed by an HttpOnly session cookie) and is sent to AgentCore Runtime
as the bearer token. One runtime session per sign-in, so the IdC token exchange happens once (single-use JWT).
Run:  infra/run.sh .venv/bin/python webchat/obo_app.py   then open http://localhost:8080"""
import base64, hashlib, html, json, os, secrets, sys, urllib.parse, urllib.request, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests"))
from invoke import invoke  # noqa: E402

DOMAIN, CLIENT = os.environ["COGNITO_DOMAIN"], os.environ["COGNITO_CLIENT_ID"]
BASE = os.environ.get("WEB_BASE_URL", "http://localhost:8080")  # Lambda Function URL when deployed (infra/14)
REDIRECT = f"{BASE}/callback"
SESSIONS, PENDING = {}, {}  # sid -> {token, user, runtime_session}; state -> code_verifier
PAGE = open(os.path.join(os.path.dirname(__file__), "index.html"), encoding="utf-8").read()


def claims(jwt):
    return json.loads(base64.urlsafe_b64decode(jwt.split(".")[1] + "=="))


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, code, body=b"", ctype="text/html; charset=utf-8", headers=()):
        self.send_response(code); self.send_header("Content-Type", ctype)
        for k, v in headers: self.send_header(k, v)
        self.end_headers(); self.wfile.write(body if isinstance(body, bytes) else body.encode())

    def session(self):
        c = dict(p.strip().split("=", 1) for p in self.headers.get("Cookie", "").split(";") if "=" in p)
        return SESSIONS.get(c.get("sid", ""))

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if u.path == "/":
            s = self.session()
            return self.send(200, PAGE.replace("__USER__", html.escape(s["user"]) if s else "")
                                      .replace("__SIGNEDIN__", "true" if s else "false"))
        if u.path == "/login":
            verifier = secrets.token_urlsafe(48); state = secrets.token_urlsafe(16); PENDING[state] = verifier
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
            params = dict(response_type="code", client_id=CLIENT, redirect_uri=REDIRECT, scope="openid email profile",
                          state=state, code_challenge=challenge, code_challenge_method="S256", prompt="login")
            return self.send(302, headers=[("Location", f"{DOMAIN}/oauth2/authorize?{urllib.parse.urlencode(params)}")])
        if u.path == "/callback":
            verifier = PENDING.pop(q.get("state", [""])[0], None)
            if not verifier or "code" not in q:
                return self.send(400, "Invalid or expired sign-in (state mismatch). <a href='/'>Back</a>")
            body = urllib.parse.urlencode(dict(grant_type="authorization_code", client_id=CLIENT, code=q["code"][0],
                                               redirect_uri=REDIRECT, code_verifier=verifier)).encode()
            req = urllib.request.Request(f"{DOMAIN}/oauth2/token", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
            tok = json.loads(urllib.request.urlopen(req, timeout=15).read())["id_token"]
            c = claims(tok); sid = secrets.token_urlsafe(24)
            SESSIONS[sid] = {"token": tok, "user": f"{c.get('cognito:username')} ({c.get('email')})",
                             "runtime_session": f"rsidc-web-{uuid.uuid4()}"}
            return self.send(302, headers=[("Location", "/"), ("Set-Cookie", f"sid={sid}; HttpOnly; SameSite=Lax; Path=/")])
        if u.path == "/logout":
            c = dict(p.strip().split("=", 1) for p in self.headers.get("Cookie", "").split(";") if "=" in p)
            SESSIONS.pop(c.get("sid", ""), None)
            lo = f"{DOMAIN}/logout?{urllib.parse.urlencode(dict(client_id=CLIENT, logout_uri=BASE + '/'))}"
            return self.send(302, headers=[("Location", lo), ("Set-Cookie", "sid=; Max-Age=0; Path=/")])
        self.send(404, "not found")

    def do_POST(self):
        s = self.session()
        if self.path != "/api/ask" or not s:
            return self.send(401, json.dumps({"error": "sign in first"}), "application/json")
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        body = {"sql": payload["sql"]} if payload.get("sql") else {"prompt": payload.get("prompt", "")}
        status, res = invoke(s["token"], body, session_id=s["runtime_session"])
        self.send(200, json.dumps({"status": status, "result": res}), "application/json")


if __name__ == "__main__":
    print("open http://localhost:8080  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", 8080), H).serve_forever()
