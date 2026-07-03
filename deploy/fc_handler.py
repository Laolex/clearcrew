"""FC entrypoint: Function Compute HTTP event -> ASGI -> clearcrew.replay.app."""
import asyncio
import base64
import json
from urllib.parse import urlencode

from clearcrew.replay import app


def _scope(e):
    http = e.get("requestContext", {}).get("http", {})
    headers = {k: v for k, v in (e.get("headers") or {}).items()}
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": "1.1",
        "method": http.get("method", "GET"),
        "path": e.get("rawPath", "/"),
        "raw_path": e.get("rawPath", "/").encode(),
        "query_string": urlencode(e.get("queryParameters") or {}).encode(),
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "scheme": headers.get("X-Forwarded-Proto", "https"),
        "server": (http.get("host", "fc"), 443),
        "client": (http.get("sourceIp", ""), 0),
        "root_path": "",
    }


async def _run(scope, body):
    resp = {"status": 500, "headers": [], "chunks": []}
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(msg):
        if msg["type"] == "http.response.start":
            resp["status"] = msg["status"]
            resp["headers"] = msg.get("headers", [])
        elif msg["type"] == "http.response.body":
            resp["chunks"].append(msg.get("body", b""))

    await app(scope, receive, send)
    return resp


def handler(event, context):
    e = json.loads(event) if isinstance(event, (str, bytes)) else event
    raw = e.get("body") or ""
    body = base64.b64decode(raw) if e.get("isBase64Encoded") else raw.encode()
    resp = asyncio.run(_run(_scope(e), body))
    return {
        "statusCode": resp["status"],
        "headers": {k.decode(): v.decode() for k, v in resp["headers"]},
        "body": base64.b64encode(b"".join(resp["chunks"])).decode(),
        "isBase64Encoded": True,
    }
