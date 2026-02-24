#!/usr/bin/env python3
"""Minimal HTTP server exposing health endpoints for pilot validation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import monotonic

START_MONOTONIC = monotonic()
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write_json(
                200,
                {
                    "status": "ok",
                    "timestamp": now_utc_iso(),
                },
            )
            return

        if self.path == "/health/details":
            self._write_json(
                200,
                {
                    "status": "ok",
                    "timestamp": now_utc_iso(),
                    "uptime_seconds": round(max(monotonic() - START_MONOTONIC, 0.0), 3),
                    "version": APP_VERSION,
                },
            )
            return

        self._write_json(404, {"error": "not_found"})

    def _write_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def run() -> None:
    port = int(os.getenv("PORT", "8000"))
    server = HTTPServer(("127.0.0.1", port), HealthHandler)
    print(f"health server listening on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
