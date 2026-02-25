#!/usr/bin/env python3
"""Minimal HTTP server exposing health endpoints for pilot validation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import monotonic

from app.notes_repo import create_note, initialize_database, list_notes

START_MONOTONIC = monotonic()
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
METRICS: dict[str, object] = {
    "requests_total": 0,
    "errors_total": 0,
    "notes_created_total": 0,
    "by_route": {},
}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def readiness_dependencies() -> dict[str, bool]:
    return {
        "db": env_bool("READY_DB", True),
        "cache": env_bool("READY_CACHE", True),
        "queue": env_bool("READY_QUEUE", True),
    }


def clear_observability_metrics() -> None:
    METRICS["requests_total"] = 0
    METRICS["errors_total"] = 0
    METRICS["notes_created_total"] = 0
    METRICS["by_route"] = {}


def _metric_route_key(method: str, path: str, status: int) -> str:
    return f"{method} {path} {status}"


def record_response_metrics(method: str, path: str, status: int) -> None:
    METRICS["requests_total"] = int(METRICS["requests_total"]) + 1
    if status >= 400:
        METRICS["errors_total"] = int(METRICS["errors_total"]) + 1
    if method == "POST" and path == "/notes" and status == 201:
        METRICS["notes_created_total"] = int(METRICS["notes_created_total"]) + 1

    by_route = METRICS["by_route"]
    assert isinstance(by_route, dict)
    key = _metric_route_key(method, path, status)
    by_route[key] = int(by_route.get(key, 0)) + 1


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        started = monotonic()
        if self.path == "/health":
            self._write_json(
                200,
                {
                    "status": "ok",
                    "timestamp": now_utc_iso(),
                },
                started,
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
                started,
            )
            return

        if self.path == "/health/ready":
            deps = readiness_dependencies()
            ready = all(deps.values())
            self._write_json(
                200 if ready else 503,
                {
                    "status": "ready" if ready else "not_ready",
                    "timestamp": now_utc_iso(),
                    "dependencies": deps,
                },
                started,
            )
            return

        if self.path == "/notes":
            self._write_json(200, {"items": list_notes()}, started)
            return

        if self.path == "/metrics":
            self._write_json(
                200,
                {
                    "status": "ok",
                    "timestamp": now_utc_iso(),
                    "uptime_seconds": round(max(monotonic() - START_MONOTONIC, 0.0), 3),
                    "metrics": METRICS,
                },
                started,
            )
            return

        self._write_json(404, {"error": "not_found"}, started)

    def do_POST(self) -> None:  # noqa: N802
        started = monotonic()
        if self.path == "/notes":
            self._handle_create_note(started)
            return
        self._write_json(404, {"error": "not_found"}, started)

    def _handle_create_note(self, started: float) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._write_json(400, {"error": "invalid_content_length"}, started)
            return

        raw_body = self.rfile.read(max(content_length, 0))
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_json(400, {"error": "invalid_json"}, started)
            return

        if not isinstance(payload, dict):
            self._write_json(400, {"error": "invalid_payload"}, started)
            return

        title = payload.get("title")
        content = payload.get("content")
        if not isinstance(title, str) or not title.strip():
            self._write_json(400, {"error": "title_required"}, started)
            return
        if content is not None and not isinstance(content, str):
            self._write_json(400, {"error": "content_must_be_string"}, started)
            return

        note = create_note(title.strip(), content, now_utc_iso())
        self._write_json(201, note, started)

    def _write_json(self, status: int, payload: dict[str, object], started: float) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        elapsed_ms = round(max(monotonic() - started, 0.0) * 1000, 3)
        method = self.command
        path = self.path
        record_response_metrics(method, path, status)
        print(
            json.dumps(
                {
                    "event": "http_request",
                    "timestamp": now_utc_iso(),
                    "method": method,
                    "path": path,
                    "status": status,
                    "duration_ms": elapsed_ms,
                },
            ),
            flush=True,
        )

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def run() -> None:
    port = int(os.getenv("PORT", "8000"))
    initialize_database()
    server = HTTPServer(("127.0.0.1", port), HealthHandler)
    print(f"health server listening on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
