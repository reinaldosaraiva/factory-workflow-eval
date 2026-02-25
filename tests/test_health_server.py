from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from datetime import datetime
from http.client import HTTPConnection
from http.server import HTTPServer

from app.health_server import APP_VERSION, HealthHandler, clear_observability_metrics
from app.notes_repo import clear_notes_store, initialize_database


class HealthServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db_file = tempfile.NamedTemporaryFile(prefix="factory-notes-", suffix=".db", delete=False)
        cls.db_file.close()
        os.environ["NOTES_DB_PATH"] = cls.db_file.name
        initialize_database()
        cls.server = HTTPServer(("127.0.0.1", 0), HealthHandler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=1)
        os.environ.pop("NOTES_DB_PATH", None)
        if os.path.exists(cls.db_file.name):
            os.remove(cls.db_file.name)

    def setUp(self) -> None:
        self._saved_env = {
            "READY_DB": os.environ.get("READY_DB"),
            "READY_CACHE": os.environ.get("READY_CACHE"),
            "READY_QUEUE": os.environ.get("READY_QUEUE"),
            "NOTES_DB_PATH": os.environ.get("NOTES_DB_PATH"),
        }
        clear_notes_store()
        clear_observability_metrics()

    def tearDown(self) -> None:
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        os.environ["NOTES_DB_PATH"] = self.db_file.name

    def request_json(self, path: str, method: str = "GET", body: str | None = None):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json"}
        conn.request(method, path, body=body, headers=headers)
        res = conn.getresponse()
        body = res.read().decode("utf-8")
        conn.close()
        return res, json.loads(body)

    def test_health_success(self) -> None:
        res, payload = self.request_json("/health")
        self.assertEqual(res.status, 200)
        self.assertEqual(res.getheader("Content-Type"), "application/json")
        self.assertEqual(payload["status"], "ok")
        datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))

    def test_health_details_success(self) -> None:
        res, payload = self.request_json("/health/details")
        self.assertEqual(res.status, 200)
        self.assertEqual(payload["status"], "ok")
        datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))
        self.assertIsInstance(payload["uptime_seconds"], (int, float))
        self.assertGreaterEqual(payload["uptime_seconds"], 0)
        self.assertEqual(payload["version"], APP_VERSION)

    def test_health_ready_success(self) -> None:
        os.environ["READY_DB"] = "true"
        os.environ["READY_CACHE"] = "true"
        os.environ["READY_QUEUE"] = "true"
        res, payload = self.request_json("/health/ready")
        self.assertEqual(res.status, 200)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["dependencies"], {"db": True, "cache": True, "queue": True})
        datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))

    def test_health_ready_not_ready(self) -> None:
        os.environ["READY_DB"] = "false"
        os.environ["READY_CACHE"] = "true"
        os.environ["READY_QUEUE"] = "true"
        res, payload = self.request_json("/health/ready")
        self.assertEqual(res.status, 503)
        self.assertEqual(payload["status"], "not_ready")
        self.assertEqual(payload["dependencies"], {"db": False, "cache": True, "queue": True})
        datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))

    def test_unknown_route(self) -> None:
        res, payload = self.request_json("/unknown")
        self.assertEqual(res.status, 404)
        self.assertEqual(payload["error"], "not_found")

    def test_create_note_success(self) -> None:
        res, payload = self.request_json(
            "/notes",
            method="POST",
            body=json.dumps({"title": "First note", "content": "details"}),
        )
        self.assertEqual(res.status, 201)
        self.assertEqual(payload["id"], 1)
        self.assertEqual(payload["title"], "First note")
        self.assertEqual(payload["content"], "details")
        datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))

    def test_list_notes_success(self) -> None:
        self.request_json(
            "/notes",
            method="POST",
            body=json.dumps({"title": "A", "content": "one"}),
        )
        self.request_json(
            "/notes",
            method="POST",
            body=json.dumps({"title": "B", "content": "two"}),
        )
        res, payload = self.request_json("/notes")
        self.assertEqual(res.status, 200)
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(payload["items"][0]["title"], "A")
        self.assertEqual(payload["items"][1]["title"], "B")

    def test_create_note_missing_title_returns_400(self) -> None:
        res, payload = self.request_json(
            "/notes",
            method="POST",
            body=json.dumps({"content": "missing title"}),
        )
        self.assertEqual(res.status, 400)
        self.assertEqual(payload["error"], "title_required")

    def test_create_note_invalid_json_returns_400(self) -> None:
        res, payload = self.request_json(
            "/notes",
            method="POST",
            body="{bad-json",
        )
        self.assertEqual(res.status, 400)
        self.assertEqual(payload["error"], "invalid_json")

    def test_notes_persist_after_server_restart(self) -> None:
        self.request_json(
            "/notes",
            method="POST",
            body=json.dumps({"title": "persisted", "content": "keep"}),
        )
        cls = type(self)
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=1)

        cls.server = HTTPServer(("127.0.0.1", 0), HealthHandler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

        res, payload = self.request_json("/notes")
        self.assertEqual(res.status, 200)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["title"], "persisted")

    def test_metrics_endpoint_reports_counters(self) -> None:
        self.request_json("/health")
        self.request_json(
            "/notes",
            method="POST",
            body=json.dumps({"title": "obs", "content": "counter"}),
        )
        self.request_json("/unknown")

        res, payload = self.request_json("/metrics")
        self.assertEqual(res.status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertGreaterEqual(payload["metrics"]["requests_total"], 3)
        self.assertGreaterEqual(payload["metrics"]["errors_total"], 1)
        self.assertGreaterEqual(payload["metrics"]["notes_created_total"], 1)


if __name__ == "__main__":
    unittest.main()
