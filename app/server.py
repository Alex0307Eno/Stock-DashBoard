from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .services import dashboard_payload, symbol_detail
from .ui import page_html


ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"


class Handler(BaseHTTPRequestHandler):
    server_version = "PythonETF/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_html(page_html())
            return
        if parsed.path == "/api/dashboard":
            query = parse_qs(parsed.query)
            stock_id = (query.get("stock") or [""])[0].strip()
            self.send_json(dashboard_payload(stock_id))
            return
        if parsed.path == "/api/symbol":
            query = parse_qs(parsed.query)
            symbol = (query.get("symbol") or ["2330.TW"])[0].strip() or "2330.TW"
            self.send_json(symbol_detail(symbol))
            return
        if parsed.path.startswith("/static/"):
            self.send_static(parsed.path.removeprefix("/static/"))
            return
        self.send_error(404, "Not found")

    def send_json(self, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, relative: str) -> None:
        path = (STATIC / relative).resolve()
        if STATIC.resolve() not in path.parents or not path.exists():
            self.send_error(404, "Static file not found")
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str | None = None, port: int | None = None) -> None:
    # Render and most free hosts require binding to 0.0.0.0 and their PORT env var.
    host = host or os.environ.get("HOST", "0.0.0.0")
    port = port or int(os.environ.get("PORT", "8088"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving Python ETF dashboard at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
