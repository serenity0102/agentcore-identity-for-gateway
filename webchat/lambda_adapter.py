"""Run the existing webchat handlers (app.py / oauth_app.py) behind a Lambda Function URL, unchanged.
The Function URL event is replayed as a raw HTTP request into the module's BaseHTTPRequestHandler `H`, and the
written HTTP response is parsed back into the Function URL response format.
Env: WEBCHAT_APP=app|oauth_app, ALLOWED_IPS="1.2.3.4/32 2400:db8:1:2::/64" (CIDRs; requestContext.http.sourceIp is set by AWS, not the client).
Sessions live in module memory, so the function runs with reserved concurrency 1 (one warm environment)."""
import base64, importlib, io, ipaddress, os, sys

sys.path.insert(0, os.path.dirname(__file__))
APP = importlib.import_module(os.environ["WEBCHAT_APP"])
ALLOWED = [ipaddress.ip_network(c, strict=False) for c in os.environ["ALLOWED_IPS"].split()]  # URL is dual-stack: include IPv6


class _Handler(APP.H):
    def __init__(self, raw, client_ip):
        self.raw = raw
        super().__init__(None, (client_ip, 0), None)

    def setup(self):
        self.rfile, self.wfile = io.BytesIO(self.raw), io.BytesIO()

    def finish(self):
        pass


def _to_raw_request(event):
    http = event["requestContext"]["http"]
    body = event.get("body") or ""
    body = base64.b64decode(body) if event.get("isBase64Encoded") else body.encode()
    target = event["rawPath"] + (f"?{event['rawQueryString']}" if event.get("rawQueryString") else "")
    headers = {k: v for k, v in event.get("headers", {}).items() if k not in ("content-length", "cookie")}
    headers["content-length"] = str(len(body))
    if event.get("cookies"):
        headers["cookie"] = "; ".join(event["cookies"])
    head = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    return f"{http['method']} {target} HTTP/1.1\r\n{head}\r\n".encode() + body


def _to_response(raw):
    head, _, body = raw.partition(b"\r\n\r\n")
    status_line, *lines = head.decode("iso-8859-1").split("\r\n")
    headers, cookies = {}, []
    for line in lines:
        k, v = line.split(":", 1)
        if k.lower() == "set-cookie":
            cookies.append(v.strip())
        else:
            headers[k] = v.strip()
    return {"statusCode": int(status_line.split()[1]), "headers": headers, "cookies": cookies,
            "body": body.decode("utf-8"), "isBase64Encoded": False}


def handler(event, _context):
    ip = event["requestContext"]["http"]["sourceIp"]
    if not any(ipaddress.ip_address(ip) in net for net in ALLOWED):
        print(f"denied source IP {ip}")
        return {"statusCode": 403, "headers": {"Content-Type": "text/plain"}, "body": f"forbidden: {ip} is not allowlisted"}
    return _to_response(_Handler(_to_raw_request(event), ip).wfile.getvalue())
