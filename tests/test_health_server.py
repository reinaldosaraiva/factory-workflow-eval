from __future__ import annotations

import json
import threading
import unittest
from datetime import datetime
from http.client import HTTPConnection
from http.server import HTTPServer

from app.health_server import HealthHandler


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

    def test_health_success(self) -> None:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/health")
        res = conn.getresponse()
        body = res.read().decode("utf-8")
        conn.close()

        self.assertEqual(res.status, 200)
        self.assertEqual(res.getheader("Content-Type"), "application/json")
        payload = json.loads(body)
        self.assertEqual(payload["status"], "ok")
        datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))

    def test_unknown_route(self) -> None:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/unknown")
        res = conn.getresponse()
        body = res.read().decode("utf-8")
        conn.close()

        self.assertEqual(res.status, 404)
        payload = json.loads(body)
        self.assertEqual(payload["error"], "not_found")


if __name__ == "__main__":
    unittest.main()
