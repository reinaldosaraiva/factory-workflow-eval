from __future__ import annotations

import json
import os
import threading
import unittest
from datetime import datetime
from http.client import HTTPConnection
from http.server import HTTPServer

from app.health_server import APP_VERSION, HealthHandler


class HealthServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = HTTPServer(("127.0.0.1", 0), HealthHandler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=1)

    def setUp(self) -> None:
        self._saved_env = {
            "READY_DB": os.environ.get("READY_DB"),
            "READY_CACHE": os.environ.get("READY_CACHE"),
            "READY_QUEUE": os.environ.get("READY_QUEUE"),
        }

    def tearDown(self) -> None:
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def request_json(self, path: str):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
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


if __name__ == "__main__":
    unittest.main()
