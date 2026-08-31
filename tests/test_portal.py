from __future__ import annotations

import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import app


class PortalIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        app.DB_PATH = Path(cls.temp_dir.name) / "ploda-test.db"
        app.ENVIRONMENT = "test"
        app.init_db()

        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.PortalHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temp_dir.cleanup()

    def setUp(self) -> None:
        self.cookie_jar = http.cookiejar.CookieJar()
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
        self.csrf = ""

    def request(self, path: str, *, method: str = "GET", payload: dict | None = None, csrf: bool = False):
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode()
        if csrf:
            headers["X-CSRF-Token"] = self.csrf
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with self.client.open(request, timeout=5) as response:
                return response.status, response.headers, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, error.headers, json.loads(error.read())

    def register(self, email: str = "member@example.com") -> dict:
        status, _, body = self.request(
            "/api/register",
            method="POST",
            payload={
                "fullName": "Portal Test Member",
                "email": email,
                "phone": "+263771000001",
                "province": "Harare",
                "password": "SecurePass1!",
                "acceptedTerms": True,
            },
        )
        self.assertEqual(status, 201)
        self.csrf = body["csrfToken"]
        return body

    def test_health_and_security_headers(self) -> None:
        status, headers, body = self.request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")

    def test_registration_authentication_and_member_workflow(self) -> None:
        body = self.register()
        self.assertRegex(body["user"]["memberNo"], r"^PLODA-\d{4}-\d{5}$")

        status, _, dashboard = self.request("/api/dashboard")
        self.assertEqual(status, 200)
        self.assertEqual(dashboard["summary"]["projects"], 3)

        status, _, profile = self.request(
            "/api/member-registration",
            method="POST",
            csrf=True,
            payload={
                "nationalId": "63-123456-A-01",
                "address": "23 Test Avenue, Harare",
                "nextOfKin": "Example Relative +263771000002",
                "occupation": "Auditor",
                "interests": "Agro-residential projects",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(profile["user"]["membershipStatus"], "Submitted for verification")

        status, _, deposit = self.request(
            "/api/deposits",
            method="POST",
            csrf=True,
            payload={"amount": 200, "currency": "USD", "method": "Cash", "note": "Joining fee"},
        )
        self.assertEqual(status, 201)
        self.assertRegex(deposit["reference"], r"^PLD-\d{8}-[A-F0-9]{6}$")

        status, _, statements = self.request("/api/statements")
        self.assertEqual(status, 200)
        self.assertEqual(len(statements["entries"]), 1)
        self.assertEqual(statements["entries"][0]["status"], "Awaiting verification")

    def test_csrf_and_password_controls(self) -> None:
        status, _, weak = self.request(
            "/api/register",
            method="POST",
            payload={
                "fullName": "Weak Password",
                "email": "weak@example.com",
                "phone": "+263771000003",
                "province": "Harare",
                "password": "password",
                "acceptedTerms": True,
            },
        )
        self.assertEqual(status, 422)
        self.assertIn("10 characters", weak["error"])

        self.register("csrf@example.com")
        status, _, body = self.request(
            "/api/deposits",
            method="POST",
            payload={"amount": 10, "currency": "USD", "method": "Cash", "note": "Test"},
        )
        self.assertEqual(status, 403)
        self.assertIn("secure session token", body["error"])

    def test_unconfigured_gateways_do_not_take_funds(self) -> None:
        self.register("gateway@example.com")
        status, _, methods = self.request("/api/payment-methods")
        self.assertEqual(status, 200)
        self.assertFalse(methods["methods"]["EcoCash"])
        self.assertFalse(methods["methods"]["PayPal"])
        self.assertTrue(methods["methods"]["Cash"])

        status, _, body = self.request(
            "/api/deposits",
            method="POST",
            csrf=True,
            payload={"amount": 10, "currency": "USD", "method": "EcoCash", "note": "Test"},
        )
        self.assertEqual(status, 503)
        self.assertIn("No funds have been taken", body["error"])


if __name__ == "__main__":
    unittest.main()
