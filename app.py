#!/usr/bin/env python3
"""PLODA member portal - dependency-free Python full-stack application.

Run locally with: python3 app.py
Production settings are documented in README.md and .env.example.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
DOCUMENTS_DIR = ROOT / "documents"
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.getenv("PLODA_DB_PATH", str(DATA_DIR / "ploda.db")))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
ENVIRONMENT = os.getenv("PLODA_ENV", "development").lower()
SESSION_SECONDS = 60 * 60 * 12
MAX_BODY = 2 * 1024 * 1024
PASSWORD_RE = re.compile(r"^(?=.{10,128}$)(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).+$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
LOGIN_WINDOW_SECONDS = 600
LOGIN_MAX_ATTEMPTS = 8
LOGIN_ATTEMPTS: dict[str, list[float]] = {}

PUBLIC_PAGES = {"/", "/signin", "/create-account", "/privacy", "/terms"}
MEMBER_PAGES = {
    "/dashboard",
    "/projects",
    "/payments",
    "/deposit",
    "/statements",
    "/documents",
    "/news",
    "/support",
    "/profile",
    "/constitution",
    "/member-registration",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().replace(microsecond=0).isoformat()


def db_connect() -> sqlite3.Connection:
    # Production can place the SQLite file on a mounted persistent disk.
    # Create the configured parent, not only the repository's default folder.
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    with db_connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_no TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                phone TEXT NOT NULL,
                province TEXT NOT NULL DEFAULT '',
                national_id TEXT NOT NULL DEFAULT '',
                address TEXT NOT NULL DEFAULT '',
                next_of_kin TEXT NOT NULL DEFAULT '',
                occupation TEXT NOT NULL DEFAULT '',
                interests TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                membership_status TEXT NOT NULL DEFAULT 'Pending verification',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS users_national_id_unique
            ON users(national_id) WHERE national_id <> '';

            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                csrf_token TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                reference TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                method TEXT NOT NULL,
                gateway_reference TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                sender TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                excerpt TEXT NOT NULL,
                published_at TEXT NOT NULL
            );
            """
        )

        if conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO projects(title, category, location, status, progress, description, created_at) VALUES(?,?,?,?,?,?,?)",
                [
                    (
                        "Agro-Residential Community Programme",
                        "Agro-residential",
                        "Zimbabwe - phased locations",
                        "Member mobilisation",
                        38,
                        "A phased programme linking dignified settlement with household crop production, livestock and sustainable land use.",
                        iso_now(),
                    ),
                    (
                        "Land Access Facilitation Initiative",
                        "Land ownership",
                        "National",
                        "Ongoing",
                        62,
                        "Structured member support for transparent land access, documentation guidance and responsible development pathways.",
                        iso_now(),
                    ),
                    (
                        "Community Enterprise & Skills Hub",
                        "Empowerment",
                        "Harare pilot",
                        "Planning",
                        24,
                        "Member-focused skills, enterprise and job-creation support aligned to productive community development.",
                        iso_now(),
                    ),
                ],
            )

        if conn.execute("SELECT COUNT(*) FROM news").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO news(title, category, excerpt, published_at) VALUES(?,?,?,?)",
                [
                    (
                        "Welcome to the PLODA Member Portal",
                        "Portal update",
                        "Members can now access projects, payments, statements, documents and support from one secure place.",
                        iso_now(),
                    ),
                    (
                        "Member Verification Guidance",
                        "Membership",
                        "Keep your profile and registration information current to support an efficient verification process.",
                        (utc_now() - timedelta(days=3)).replace(microsecond=0).isoformat(),
                    ),
                    (
                        "Responsible Payment Notice",
                        "Payments",
                        "Only use payment channels shown inside the authenticated portal and retain your transaction reference.",
                        (utc_now() - timedelta(days=8)).replace(microsecond=0).isoformat(),
                    ),
                ],
            )


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 310_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode().rstrip("="),
        base64.urlsafe_b64encode(digest).decode().rstrip("="),
    )


def password_verify(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_text, digest_text = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text + "==")
        expected = base64.urlsafe_b64decode(digest_text + "==")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def clean_text(value: Any, maximum: int = 250) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())[:maximum]


def member_number(user_id: int) -> str:
    return f"PLODA-{utc_now().year}-{user_id:05d}"


def gateway_configuration() -> dict[str, bool]:
    return {
        "EcoCash": bool(
            os.getenv("ECOCASH_API_URL")
            and os.getenv("ECOCASH_API_KEY")
            and os.getenv("ECOCASH_MERCHANT_ID")
            and os.getenv("ECOCASH_WEBHOOK_SECRET")
        ),
        "Bank transfer": bool(os.getenv("BANK_ACCOUNT_NAME") and os.getenv("BANK_ACCOUNT_NUMBER")),
        "Visa": bool(os.getenv("VISA_CHECKOUT_URL")),
        "Cash": True,
        "PayPal": bool(os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET")),
    }


def public_base_url(handler: BaseHTTPRequestHandler) -> str:
    if BASE_URL:
        return BASE_URL
    scheme = handler.headers.get("X-Forwarded-Proto", "http")
    host = handler.headers.get("X-Forwarded-Host") or handler.headers.get("Host", f"localhost:{PORT}")
    return f"{scheme}://{host}"


def remote_ip(handler: BaseHTTPRequestHandler) -> str:
    forwarded = handler.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    return forwarded or handler.client_address[0]


def login_allowed(ip: str) -> bool:
    cutoff = time.time() - LOGIN_WINDOW_SECONDS
    attempts = [item for item in LOGIN_ATTEMPTS.get(ip, []) if item > cutoff]
    LOGIN_ATTEMPTS[ip] = attempts
    return len(attempts) < LOGIN_MAX_ATTEMPTS


def record_login_failure(ip: str) -> None:
    LOGIN_ATTEMPTS.setdefault(ip, []).append(time.time())


class PortalHandler(BaseHTTPRequestHandler):
    server_version = "PLODAPortal/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        if ENVIRONMENT == "development":
            super().log_message(fmt, *args)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; form-action 'self' https://www.paypal.com https://www.sandbox.paypal.com; frame-ancestors 'none'; base-uri 'self'")
        if ENVIRONMENT == "production":
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        super().end_headers()

    def send_json(self, payload: Any, status: int = 200, extra_headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, body: bytes, content_type: str, status: int = 200, cache: str = "no-store") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json({"error": "Invalid request length."}, 400)
            return None
        if length <= 0 or length > MAX_BODY:
            self.send_json({"error": "Invalid request body."}, 400)
            return None
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError
            return value
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self.send_json({"error": "Invalid JSON request."}, 400)
            return None

    def cookies(self) -> SimpleCookie:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            pass
        return cookie

    def current_session(self) -> tuple[sqlite3.Row, sqlite3.Row] | None:
        morsel = self.cookies().get("ploda_session")
        if not morsel:
            return None
        with db_connect() as conn:
            row = conn.execute(
                "SELECT s.*, u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?",
                (token_hash(morsel.value),),
            ).fetchone()
            if not row:
                return None
            try:
                if datetime.fromisoformat(row["expires_at"]) <= utc_now():
                    conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(morsel.value),))
                    return None
            except ValueError:
                return None
            session = conn.execute("SELECT * FROM sessions WHERE token_hash=?", (token_hash(morsel.value),)).fetchone()
            user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
            return session, user

    def require_auth(self, csrf: bool = False) -> tuple[sqlite3.Row, sqlite3.Row] | None:
        auth = self.current_session()
        if not auth:
            self.send_json({"error": "Authentication required."}, 401)
            return None
        if csrf and not hmac.compare_digest(self.headers.get("X-CSRF-Token", ""), auth[0]["csrf_token"]):
            self.send_json({"error": "Your secure session token is invalid. Refresh the page and try again."}, 403)
            return None
        return auth

    def set_session_cookie(self, token: str) -> str:
        secure = "; Secure" if ENVIRONMENT == "production" else ""
        return f"ploda_session={token}; Path=/; Max-Age={SESSION_SECONDS}; HttpOnly; SameSite=Lax{secure}"

    def clear_session_cookie(self) -> str:
        secure = "; Secure" if ENVIRONMENT == "production" else ""
        return f"ploda_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax{secure}"

    def serve_static(self, path: str) -> None:
        relative = path[len("/static/") :]
        candidate = (STATIC_DIR / relative).resolve()
        try:
            candidate.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self.send_error(404)
            return
        if not candidate.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        cache = "public, max-age=3600" if candidate.suffix in {".css", ".js", ".svg", ".png", ".jpg", ".woff2"} else "no-store"
        self.send_bytes(candidate.read_bytes(), content_type, cache=cache)

    def serve_document(self, filename: str) -> None:
        auth = self.require_auth()
        if not auth:
            return
        candidate = (DOCUMENTS_DIR / filename).resolve()
        try:
            candidate.relative_to(DOCUMENTS_DIR.resolve())
        except ValueError:
            self.send_error(404)
            return
        if not candidate.is_file():
            self.send_json({"error": "The document is not available yet."}, 404)
            return
        body = candidate.read_bytes()
        mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", f'attachment; filename="{candidate.name}"')
        self.send_header("Cache-Control", "private, max-age=300")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path.startswith("/static/"):
            self.serve_static(path)
            return
        if path.startswith("/downloads/"):
            self.serve_document(path[len("/downloads/") :])
            return
        if path == "/health":
            self.send_json({"status": "ok", "service": "PLODA Member Portal"})
            return
        if path == "/api/me":
            self.api_me()
            return
        if path == "/api/dashboard":
            self.api_dashboard()
            return
        if path == "/api/projects":
            self.api_projects()
            return
        if path == "/api/payments":
            self.api_payments()
            return
        if path == "/api/statements":
            self.api_statements()
            return
        if path == "/api/news":
            self.api_news()
            return
        if path == "/api/support/messages":
            self.api_support_messages()
            return
        if path == "/api/payment-methods":
            self.api_payment_methods()
            return
        if path == "/payment/paypal/return":
            self.paypal_return(parsed.query)
            return
        if path in PUBLIC_PAGES or path in MEMBER_PAGES:
            if path in MEMBER_PAGES and not self.current_session():
                self.send_response(302)
                self.send_header("Location", "/signin?next=" + urllib.parse.quote(path))
                self.end_headers()
                return
            self.send_bytes((STATIC_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        routes = {
            "/api/register": self.api_register,
            "/api/login": self.api_login,
            "/api/logout": self.api_logout,
            "/api/deposits": self.api_deposit,
            "/api/support/messages": self.api_support_send,
            "/api/profile": self.api_profile_update,
            "/api/member-registration": self.api_member_registration,
            "/api/payment-callback/ecocash": self.api_ecocash_callback,
        }
        handler = routes.get(path)
        if not handler:
            self.send_error(404)
            return
        handler()

    def api_me(self) -> None:
        auth = self.current_session()
        if not auth:
            self.send_json({"authenticated": False})
            return
        session, user = auth
        self.send_json(
            {
                "authenticated": True,
                "csrfToken": session["csrf_token"],
                "user": self.public_user(user),
            }
        )

    @staticmethod
    def public_user(user: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": user["id"],
            "memberNo": user["member_no"],
            "fullName": user["full_name"],
            "email": user["email"],
            "phone": user["phone"],
            "province": user["province"],
            "nationalId": user["national_id"],
            "address": user["address"],
            "nextOfKin": user["next_of_kin"],
            "occupation": user["occupation"],
            "interests": user["interests"],
            "membershipStatus": user["membership_status"],
            "createdAt": user["created_at"],
        }

    def api_register(self) -> None:
        body = self.read_json()
        if body is None:
            return
        full_name = clean_text(body.get("fullName"), 120)
        email = clean_text(body.get("email"), 180).lower()
        phone = clean_text(body.get("phone"), 40)
        province = clean_text(body.get("province"), 80)
        password = body.get("password", "") if isinstance(body.get("password"), str) else ""
        accepted = body.get("acceptedTerms") is True

        if len(full_name.split()) < 2:
            self.send_json({"error": "Enter your full name."}, 422)
            return
        if not EMAIL_RE.fullmatch(email):
            self.send_json({"error": "Enter a valid email address."}, 422)
            return
        if len(phone) < 7:
            self.send_json({"error": "Enter a valid phone number."}, 422)
            return
        if not province:
            self.send_json({"error": "Select your province."}, 422)
            return
        if not PASSWORD_RE.fullmatch(password):
            self.send_json({"error": "Password must contain at least 10 characters, including uppercase, lowercase, a number and a special character."}, 422)
            return
        if not accepted:
            self.send_json({"error": "Accept the portal terms to continue."}, 422)
            return

        created = iso_now()
        try:
            with db_connect() as conn:
                cursor = conn.execute(
                    "INSERT INTO users(member_no,full_name,email,phone,province,password_hash,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                    (f"PENDING-{secrets.token_hex(5)}", full_name, email, phone, province, password_hash(password), created, created),
                )
                user_id = int(cursor.lastrowid)
                number = member_number(user_id)
                conn.execute("UPDATE users SET member_no=? WHERE id=?", (number, user_id))
                token, csrf, expiry = self.create_session(conn, user_id)
                user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        except sqlite3.IntegrityError:
            self.send_json({"error": "An account with this email address already exists."}, 409)
            return

        self.send_json(
            {"message": "Your PLODA account has been created.", "csrfToken": csrf, "user": self.public_user(user), "expiresAt": expiry},
            201,
            {"Set-Cookie": self.set_session_cookie(token)},
        )

    def create_session(self, conn: sqlite3.Connection, user_id: int) -> tuple[str, str, str]:
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        expiry = (utc_now() + timedelta(seconds=SESSION_SECONDS)).replace(microsecond=0).isoformat()
        conn.execute("DELETE FROM sessions WHERE user_id=? OR expires_at<=?", (user_id, iso_now()))
        conn.execute(
            "INSERT INTO sessions(token_hash,user_id,csrf_token,expires_at,created_at) VALUES(?,?,?,?,?)",
            (token_hash(token), user_id, csrf, expiry, iso_now()),
        )
        return token, csrf, expiry

    def api_login(self) -> None:
        ip = remote_ip(self)
        if not login_allowed(ip):
            self.send_json({"error": "Too many sign-in attempts. Please wait ten minutes and try again."}, 429)
            return
        body = self.read_json()
        if body is None:
            return
        email = clean_text(body.get("email"), 180).lower()
        password = body.get("password", "") if isinstance(body.get("password"), str) else ""
        with db_connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if not user or not password_verify(password, user["password_hash"]):
                record_login_failure(ip)
                time.sleep(0.15)
                self.send_json({"error": "The email address or password is incorrect."}, 401)
                return
            token, csrf, expiry = self.create_session(conn, user["id"])
        LOGIN_ATTEMPTS.pop(ip, None)
        self.send_json(
            {"message": "Welcome back.", "csrfToken": csrf, "user": self.public_user(user), "expiresAt": expiry},
            200,
            {"Set-Cookie": self.set_session_cookie(token)},
        )

    def api_logout(self) -> None:
        auth = self.require_auth(csrf=True)
        if not auth:
            return
        morsel = self.cookies().get("ploda_session")
        if morsel:
            with db_connect() as conn:
                conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(morsel.value),))
        self.send_json({"message": "You have been signed out."}, 200, {"Set-Cookie": self.clear_session_cookie()})

    def api_dashboard(self) -> None:
        auth = self.require_auth()
        if not auth:
            return
        user = auth[1]
        with db_connect() as conn:
            totals = conn.execute(
                "SELECT COALESCE(SUM(CASE WHEN status='Completed' THEN amount ELSE 0 END),0) paid, COUNT(*) count FROM payments WHERE user_id=?",
                (user["id"],),
            ).fetchone()
            recent = [dict(row) for row in conn.execute("SELECT reference,amount,currency,method,status,created_at FROM payments WHERE user_id=? ORDER BY id DESC LIMIT 5", (user["id"],))]
            project_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            unread_news = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
        self.send_json(
            {
                "summary": {
                    "totalPaid": totals["paid"],
                    "paymentCount": totals["count"],
                    "projects": project_count,
                    "news": unread_news,
                    "membershipStatus": user["membership_status"],
                },
                "recentPayments": recent,
            }
        )

    def api_projects(self) -> None:
        if not self.require_auth():
            return
        with db_connect() as conn:
            rows = [dict(row) for row in conn.execute("SELECT * FROM projects ORDER BY id")]
        self.send_json({"projects": rows})

    def api_payments(self) -> None:
        auth = self.require_auth()
        if not auth:
            return
        with db_connect() as conn:
            rows = [dict(row) for row in conn.execute("SELECT reference,amount,currency,method,status,note,created_at,updated_at FROM payments WHERE user_id=? ORDER BY id DESC", (auth[1]["id"],))]
        self.send_json({"payments": rows})

    def api_statements(self) -> None:
        auth = self.require_auth()
        if not auth:
            return
        with db_connect() as conn:
            rows = [dict(row) for row in conn.execute("SELECT reference,created_at,method,amount,currency,status,note FROM payments WHERE user_id=? ORDER BY id DESC", (auth[1]["id"],))]
        running = 0.0
        for item in reversed(rows):
            if item["status"] == "Completed":
                running += float(item["amount"])
            item["balance"] = running
        rows.reverse()
        self.send_json({"entries": rows})

    def api_news(self) -> None:
        if not self.require_auth():
            return
        with db_connect() as conn:
            rows = [dict(row) for row in conn.execute("SELECT * FROM news ORDER BY published_at DESC")]
        self.send_json({"news": rows})

    def api_support_messages(self) -> None:
        auth = self.require_auth()
        if not auth:
            return
        with db_connect() as conn:
            rows = [dict(row) for row in conn.execute("SELECT id,sender,body,created_at FROM support_messages WHERE user_id=? ORDER BY id", (auth[1]["id"],))]
        self.send_json({"messages": rows})

    def api_support_send(self) -> None:
        auth = self.require_auth(csrf=True)
        if not auth:
            return
        body = self.read_json()
        if body is None:
            return
        message = clean_text(body.get("message"), 1000)
        if len(message) < 2:
            self.send_json({"error": "Enter a message for the support team."}, 422)
            return
        created = iso_now()
        with db_connect() as conn:
            conn.execute("INSERT INTO support_messages(user_id,sender,body,created_at) VALUES(?,?,?,?)", (auth[1]["id"], "member", message, created))
            count = conn.execute("SELECT COUNT(*) FROM support_messages WHERE user_id=?", (auth[1]["id"],)).fetchone()[0]
            if count == 1:
                conn.execute(
                    "INSERT INTO support_messages(user_id,sender,body,created_at) VALUES(?,?,?,?)",
                    (auth[1]["id"], "support", "Thank you for contacting PLODA Support. Your message has been recorded and a member of our team will respond through this chat.", iso_now()),
                )
        self.send_json({"message": "Your support message has been sent."}, 201)

    def api_profile_update(self) -> None:
        auth = self.require_auth(csrf=True)
        if not auth:
            return
        body = self.read_json()
        if body is None:
            return
        full_name = clean_text(body.get("fullName"), 120)
        phone = clean_text(body.get("phone"), 40)
        province = clean_text(body.get("province"), 80)
        address = clean_text(body.get("address"), 240)
        occupation = clean_text(body.get("occupation"), 120)
        if len(full_name.split()) < 2 or len(phone) < 7 or not province:
            self.send_json({"error": "Full name, phone number and province are required."}, 422)
            return
        with db_connect() as conn:
            conn.execute(
                "UPDATE users SET full_name=?,phone=?,province=?,address=?,occupation=?,updated_at=? WHERE id=?",
                (full_name, phone, province, address, occupation, iso_now(), auth[1]["id"]),
            )
            user = conn.execute("SELECT * FROM users WHERE id=?", (auth[1]["id"],)).fetchone()
        self.send_json({"message": "Profile updated successfully.", "user": self.public_user(user)})

    def api_member_registration(self) -> None:
        auth = self.require_auth(csrf=True)
        if not auth:
            return
        body = self.read_json()
        if body is None:
            return
        fields = {
            "national_id": clean_text(body.get("nationalId"), 60),
            "address": clean_text(body.get("address"), 240),
            "next_of_kin": clean_text(body.get("nextOfKin"), 160),
            "occupation": clean_text(body.get("occupation"), 120),
            "interests": clean_text(body.get("interests"), 400),
        }
        if any(not value for value in fields.values()):
            self.send_json({"error": "Complete all member registration fields."}, 422)
            return
        try:
            with db_connect() as conn:
                conn.execute(
                    "UPDATE users SET national_id=?,address=?,next_of_kin=?,occupation=?,interests=?,membership_status='Submitted for verification',updated_at=? WHERE id=?",
                    (*fields.values(), iso_now(), auth[1]["id"]),
                )
                user = conn.execute("SELECT * FROM users WHERE id=?", (auth[1]["id"],)).fetchone()
        except sqlite3.IntegrityError:
            self.send_json({"error": "This national ID or passport number is already registered."}, 409)
            return
        self.send_json({"message": "Your member registration has been submitted for verification.", "user": self.public_user(user)})

    def api_payment_methods(self) -> None:
        if not self.require_auth():
            return
        bank = {
            "bankName": os.getenv("BANK_NAME", "To be configured"),
            "accountName": os.getenv("BANK_ACCOUNT_NAME", "To be configured"),
            "accountNumber": os.getenv("BANK_ACCOUNT_NUMBER", "To be configured"),
            "branch": os.getenv("BANK_BRANCH", "To be configured"),
        }
        self.send_json({"methods": gateway_configuration(), "bank": bank})

    def api_deposit(self) -> None:
        auth = self.require_auth(csrf=True)
        if not auth:
            return
        body = self.read_json()
        if body is None:
            return
        try:
            amount = round(float(body.get("amount")), 2)
        except (TypeError, ValueError):
            self.send_json({"error": "Enter a valid deposit amount."}, 422)
            return
        method = clean_text(body.get("method"), 40)
        currency = clean_text(body.get("currency"), 8)
        note = clean_text(body.get("note"), 300)
        allowed_methods = {"EcoCash", "Bank transfer", "Visa", "Cash", "PayPal"}
        if amount <= 0 or amount > 1_000_000:
            self.send_json({"error": "Deposit amount must be greater than zero."}, 422)
            return
        if method not in allowed_methods or currency not in {"USD", "ZiG"}:
            self.send_json({"error": "Select a supported payment method and currency."}, 422)
            return
        if method == "PayPal" and currency != "USD":
            self.send_json({"error": "PayPal deposits are currently available in USD only."}, 422)
            return
        configured = gateway_configuration()[method]
        if method in {"EcoCash", "Visa", "PayPal", "Bank transfer"} and not configured:
            self.send_json({"error": f"{method} is awaiting secure merchant configuration. No funds have been taken."}, 503)
            return

        reference = "PLD-" + utc_now().strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper()
        status = "Awaiting verification" if method in {"Bank transfer", "Cash"} else "Initiated"
        now = iso_now()
        with db_connect() as conn:
            conn.execute(
                "INSERT INTO payments(user_id,reference,amount,currency,method,status,note,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (auth[1]["id"], reference, amount, currency, method, status, note, now, now),
            )

        if method == "Bank transfer":
            self.send_json({"message": "Deposit request recorded. Use your PLODA reference when making the bank transfer.", "reference": reference, "redirectUrl": None}, 201)
            return
        if method == "Cash":
            self.send_json({"message": "Cash deposit request recorded. Pay only at an authorised PLODA office and obtain an official receipt.", "reference": reference, "redirectUrl": None}, 201)
            return
        if method == "Visa":
            url = os.environ["VISA_CHECKOUT_URL"]
            params = urllib.parse.urlencode({"reference": reference, "amount": f"{amount:.2f}", "currency": currency, "return_url": public_base_url(self) + "/payments"})
            separator = "&" if "?" in url else "?"
            self.send_json({"message": "Continue to the secure card checkout.", "reference": reference, "redirectUrl": url + separator + params}, 201)
            return
        if method == "PayPal":
            try:
                redirect = self.create_paypal_order(reference, amount, currency)
            except RuntimeError as exc:
                self.update_payment(reference, "Gateway error", str(exc))
                self.send_json({"error": "PayPal could not start the payment. No funds have been taken."}, 502)
                return
            self.send_json({"message": "Continue to PayPal to approve the payment.", "reference": reference, "redirectUrl": redirect}, 201)
            return
        if method == "EcoCash":
            try:
                redirect, gateway_ref = self.create_ecocash_payment(reference, amount, currency, auth[1])
            except RuntimeError:
                self.update_payment(reference, "Gateway error", "EcoCash initiation failed")
                self.send_json({"error": "EcoCash could not start the payment. No funds have been taken."}, 502)
                return
            self.update_payment(reference, "Initiated", "EcoCash payment initiated", gateway_ref)
            self.send_json({"message": "Approve the EcoCash payment using the secure prompt.", "reference": reference, "redirectUrl": redirect}, 201)

    def update_payment(self, reference: str, status: str, note: str = "", gateway_reference: str = "") -> None:
        with db_connect() as conn:
            conn.execute(
                "UPDATE payments SET status=?,note=?,gateway_reference=CASE WHEN ?='' THEN gateway_reference ELSE ? END,updated_at=? WHERE reference=?",
                (status, note, gateway_reference, gateway_reference, iso_now(), reference),
            )

    def paypal_token(self) -> str:
        client_id = os.environ["PAYPAL_CLIENT_ID"]
        secret = os.environ["PAYPAL_CLIENT_SECRET"]
        mode = os.getenv("PAYPAL_MODE", "live").lower()
        api = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
        credentials = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
        request = urllib.request.Request(
            api + "/v1/oauth2/token",
            data=b"grant_type=client_credentials",
            headers={"Authorization": "Basic " + credentials, "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read())["access_token"]
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError("PayPal authentication failed") from exc

    def create_paypal_order(self, reference: str, amount: float, currency: str) -> str:
        mode = os.getenv("PAYPAL_MODE", "live").lower()
        api = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{"reference_id": reference, "amount": {"currency_code": "USD" if currency == "USD" else currency, "value": f"{amount:.2f}"}}],
            "payment_source": {"paypal": {"experience_context": {"brand_name": "PLODA", "user_action": "PAY_NOW", "return_url": public_base_url(self) + "/payment/paypal/return", "cancel_url": public_base_url(self) + "/deposit?cancelled=1"}}},
        }
        request = urllib.request.Request(
            api + "/v2/checkout/orders",
            data=json.dumps(payload).encode(),
            headers={"Authorization": "Bearer " + self.paypal_token(), "Content-Type": "application/json", "PayPal-Request-Id": reference},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read())
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("PayPal order creation failed") from exc
        order_id = clean_text(data.get("id"), 120)
        approve = next((item.get("href") for item in data.get("links", []) if item.get("rel") in {"payer-action", "approve"}), None)
        if not order_id or not approve:
            raise RuntimeError("PayPal returned an incomplete order")
        self.update_payment(reference, "Awaiting approval", "PayPal order created", order_id)
        return str(approve)

    def paypal_return(self, query: str) -> None:
        auth = self.current_session()
        if not auth:
            self.send_response(302)
            self.send_header("Location", "/signin")
            self.end_headers()
            return
        params = urllib.parse.parse_qs(query)
        order_id = clean_text((params.get("token") or [""])[0], 120)
        if not order_id:
            self.send_response(302)
            self.send_header("Location", "/payments?payment=error")
            self.end_headers()
            return
        with db_connect() as conn:
            payment = conn.execute("SELECT * FROM payments WHERE gateway_reference=? AND user_id=?", (order_id, auth[1]["id"])).fetchone()
        if not payment:
            self.send_response(302)
            self.send_header("Location", "/payments?payment=error")
            self.end_headers()
            return
        mode = os.getenv("PAYPAL_MODE", "live").lower()
        api = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
        request = urllib.request.Request(
            api + f"/v2/checkout/orders/{urllib.parse.quote(order_id)}/capture",
            data=b"{}",
            headers={"Authorization": "Bearer " + self.paypal_token(), "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read())
            completed = data.get("status") == "COMPLETED"
        except (urllib.error.URLError, json.JSONDecodeError, RuntimeError):
            completed = False
        self.update_payment(payment["reference"], "Completed" if completed else "Verification required", "PayPal payment captured" if completed else "PayPal capture requires review", order_id)
        self.send_response(302)
        self.send_header("Location", "/payments?payment=" + ("success" if completed else "review"))
        self.end_headers()

    def create_ecocash_payment(self, reference: str, amount: float, currency: str, user: sqlite3.Row) -> tuple[str | None, str]:
        payload = {
            "merchant_id": os.environ["ECOCASH_MERCHANT_ID"],
            "reference": reference,
            "amount": amount,
            "currency": currency,
            "phone": user["phone"],
            "callback_url": public_base_url(self) + "/api/payment-callback/ecocash",
            "return_url": public_base_url(self) + "/payments",
        }
        request = urllib.request.Request(
            os.environ["ECOCASH_API_URL"],
            data=json.dumps(payload).encode(),
            headers={"Authorization": "Bearer " + os.environ["ECOCASH_API_KEY"], "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                data = json.loads(response.read())
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("EcoCash initiation failed") from exc
        gateway_ref = clean_text(data.get("transaction_id") or data.get("reference"), 150)
        if not gateway_ref:
            raise RuntimeError("EcoCash response did not include a transaction reference")
        return data.get("redirect_url"), gateway_ref

    def api_ecocash_callback(self) -> None:
        secret = os.getenv("ECOCASH_WEBHOOK_SECRET")
        supplied = self.headers.get("X-Webhook-Secret", "")
        if not secret or not hmac.compare_digest(secret, supplied):
            self.send_json({"error": "Invalid webhook signature."}, 403)
            return
        body = self.read_json()
        if body is None:
            return
        reference = clean_text(body.get("reference"), 80)
        gateway_ref = clean_text(body.get("transaction_id"), 150)
        raw_status = clean_text(body.get("status"), 40).lower()
        status = "Completed" if raw_status in {"paid", "completed", "success", "successful"} else "Failed" if raw_status in {"failed", "declined", "cancelled"} else "Verification required"
        if not reference:
            self.send_json({"error": "Missing payment reference."}, 422)
            return
        self.update_payment(reference, status, "EcoCash gateway update", gateway_ref)
        self.send_json({"received": True})


def main() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), PortalHandler)
    print(f"PLODA Member Portal running on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
