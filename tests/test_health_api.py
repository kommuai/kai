import unittest

from fastapi.testclient import TestClient

from app import app


class HealthApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_liveness(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("status"), "ok")

    def test_readiness(self):
        r = self.client.get("/ready")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn(body.get("status"), {"ready", "degraded"})
        self.assertIn("tenant_id", body)
        self.assertIn("tools_enabled", body)


if __name__ == "__main__":
    unittest.main()
