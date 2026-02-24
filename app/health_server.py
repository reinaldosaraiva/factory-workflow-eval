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
NOTES: list[dict[str, object]] = []
NEXT_NOTE_ID = 1


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


def clear_notes_store() -> None:
    global NEXT_NOTE_ID
    NOTES.clear()
    NEXT_NOTE_ID = 1


def create_note(title: str, content: str | None) -> dict[str, object]:
    global NEXT_NOTE_ID
    note = {
        "id": NEXT_NOTE_ID,
        "title": title,
        "content": content,
        "created_at": now_utc_iso(),
    }
    NOTES.append(note)
    NEXT_NOTE_ID += 1
    return note


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
            )
            return

        if self.path == "/notes":
            self._write_json(200, {"items": NOTES})
            return

        self._write_json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/notes":
            self._handle_create_note()
            return
        self._write_json(404, {"error": "not_found"})

    def _handle_create_note(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._write_json(400, {"error": "invalid_content_length"})
            return

        raw_body = self.rfile.read(max(content_length, 0))
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_json(400, {"error": "invalid_json"})
            return

        if not isinstance(payload, dict):
            self._write_json(400, {"error": "invalid_payload"})
            return

        title = payload.get("title")
        content = payload.get("content")
        if not isinstance(title, str) or not title.strip():
            self._write_json(400, {"error": "title_required"})
            return
        if content is not None and not isinstance(content, str):
            self._write_json(400, {"error": "content_must_be_string"})
            return

        note = create_note(title.strip(), content)
        self._write_json(201, note)

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
