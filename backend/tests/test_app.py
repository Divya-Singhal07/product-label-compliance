"""
tests/test_app.py
-----------------
Unit / integration tests for the Label Lens FastAPI backend.

All Supabase calls are mocked so no real network credentials are needed.
Run with:
    pytest product-label-compliance/backend/tests/ -v
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Make sure the backend package is importable when running from the repo root
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ---------------------------------------------------------------------------
# Stub out heavy OCR dependencies so tests don't need PaddleOCR / cv2 etc.
# ---------------------------------------------------------------------------
def _stub_module(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod

for _mod in [
    "label_lens",
    "label_lens.preprocessing",
    "label_lens.preprocessing.pipeline",
    "label_lens.ocr",
    "label_lens.ocr.ocr_pipeline",
    "label_lens.ocr.llm_extractor",
    "label_lens.ocr.product_id",
    "label_lens.rule_engine",
    "label_lens.rule_engine.engine",
    "label_lens.rule_engine_mapper",
]:
    if _mod not in sys.modules:
        _stub_module(_mod)

# Provide minimal callables so the import of ocr_routes succeeds
sys.modules["label_lens.preprocessing.pipeline"].PackageImagePreprocessor = MagicMock()
sys.modules["label_lens.ocr.ocr_pipeline"].OCRProcessor = MagicMock()
sys.modules["label_lens.ocr.llm_extractor"].extract_fields_with_llm = MagicMock()
sys.modules["label_lens.ocr.product_id"].generate_product_id = MagicMock()
sys.modules["label_lens.rule_engine_mapper"].map_to_rule_engine = MagicMock()
sys.modules["label_lens.rule_engine.engine"].run_compliance_check = MagicMock()

# ---------------------------------------------------------------------------
# Import the app (after stubs are in place)
# ---------------------------------------------------------------------------
from app import app, set_session_cookies, clear_session_cookies, ACCESS_COOKIE, REFRESH_COOKIE  # noqa: E402
from deps import auth_error_message  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


# ===========================================================================
# Helpers / fixtures
# ===========================================================================

def _make_supabase_session(access: str = "access_tok", refresh: str = "refresh_tok"):
    """Return a mock Supabase auth result with a valid session."""
    session = MagicMock()
    session.access_token = access
    session.refresh_token = refresh
    result = MagicMock()
    result.session = session
    return result


def _make_supabase_user(email: str = "test@example.com", uid: str = "uid-123"):
    user = MagicMock()
    user.email = email
    user.id = uid
    return user


# ===========================================================================
# deps.py -- auth_error_message
# ===========================================================================

class TestAuthErrorMessage:
    def test_uses_message_attribute(self):
        exc = Exception("fallback")
        exc.message = "nice error"  # type: ignore[attr-defined]
        assert auth_error_message(exc) == "nice error"

    def test_falls_back_to_str(self):
        exc = ValueError("some problem")
        assert auth_error_message(exc) == "some problem"

    def test_empty_string_fallback(self):
        exc = Exception("")
        assert auth_error_message(exc) == "Something went wrong. Please try again."


# ===========================================================================
# Cookie helpers
# ===========================================================================

class TestCookieHelpers:
    def test_set_session_cookies_sets_both(self):
        from fastapi.responses import RedirectResponse
        resp = RedirectResponse(url="/account", status_code=303)
        set_session_cookies(resp, "acc", "ref")
        raw = resp.headers.getlist("set-cookie")
        raw_joined = " ".join(raw)
        assert ACCESS_COOKIE in raw_joined
        assert REFRESH_COOKIE in raw_joined

    def test_clear_session_cookies_deletes_both(self):
        from fastapi.responses import RedirectResponse
        resp = RedirectResponse(url="/", status_code=303)
        clear_session_cookies(resp)
        raw = " ".join(resp.headers.getlist("set-cookie"))
        assert ACCESS_COOKIE in raw
        assert REFRESH_COOKIE in raw


# ===========================================================================
# GET /  (root API status)
# ===========================================================================

class TestRootEndpoint:
    def test_root_returns_status(self):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "online"
        assert "service" in data


# ===========================================================================
# OCR routes -- auth guard
# ===========================================================================

# ---------------------------------------------------------------------------
# OCR dependency override helper
# ---------------------------------------------------------------------------
import deps as _deps_module  # noqa: E402  (already imported transitively)

def _ocr_auth_override(user):
    """Return a callable that FastAPI will use instead of get_current_user."""
    def _override():
        return user
    return _override

def _ocr_auth_raise():
    """Override that always raises 401."""
    from fastapi import HTTPException
    raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")


class TestOCRRoutes:
    def setup_method(self):
        """Ensure no leftover dependency overrides between tests."""
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_create_job_without_auth_returns_401(self):
        from io import BytesIO
        app.dependency_overrides[_deps_module.get_current_user] = _ocr_auth_raise
        r = client.post(
            "/api/v1/ocr/jobs",
            files={"files": ("img.png", BytesIO(b"data"), "image/png")},
            follow_redirects=False,
        )
        assert r.status_code == 401

    def test_get_job_not_found_returns_404(self):
        user = _make_supabase_user()
        app.dependency_overrides[_deps_module.get_current_user] = _ocr_auth_override(user)
        r = client.get("/api/v1/ocr/jobs/nonexistent-id")
        assert r.status_code == 404

    def test_runtime_status_does_not_expose_configuration_values(self):
        user = _make_supabase_user()
        app.dependency_overrides[_deps_module.get_current_user] = _ocr_auth_override(user)
        r = client.get("/api/v1/ocr/runtime")
        assert r.status_code == 200
        data = r.json()
        assert data["backend_revision"] == "llm-required-v1"
        assert "GROQ_API_KEY" not in str(data)

    def test_get_job_result_not_found_returns_404(self):
        user = _make_supabase_user()
        app.dependency_overrides[_deps_module.get_current_user] = _ocr_auth_override(user)
        r = client.get("/api/v1/ocr/jobs/nonexistent-id/result")
        assert r.status_code == 404

    def test_get_job_result_pending_returns_409(self):
        from ocr_routes import _JOBS
        user = _make_supabase_user(uid="owner-uid")
        app.dependency_overrides[_deps_module.get_current_user] = _ocr_auth_override(user)
        _JOBS["test-job-id"] = {
            "status": "processing",
            "owner": "owner-uid",
            "created_at": "2026-01-01T00:00:00Z",
        }
        r = client.get("/api/v1/ocr/jobs/test-job-id/result")
        assert r.status_code == 409
        _JOBS.pop("test-job-id", None)

    def test_get_job_ownership_enforced(self):
        from ocr_routes import _JOBS
        user = _make_supabase_user(uid="other-uid")
        app.dependency_overrides[_deps_module.get_current_user] = _ocr_auth_override(user)
        _JOBS["job-owner-test"] = {
            "status": "queued",
            "owner": "real-owner-uid",
            "created_at": "2026-01-01T00:00:00Z",
        }
        r = client.get("/api/v1/ocr/jobs/job-owner-test")
        assert r.status_code == 403
        _JOBS.pop("job-owner-test", None)

    def test_get_job_status_returns_correct_info(self):
        from ocr_routes import _JOBS
        user = _make_supabase_user(uid="uid-abc")
        app.dependency_overrides[_deps_module.get_current_user] = _ocr_auth_override(user)
        _JOBS["good-job"] = {
            "status": "queued",
            "owner": "uid-abc",
            "created_at": "2026-01-01T00:00:00Z",
        }
        r = client.get("/api/v1/ocr/jobs/good-job")
        assert r.status_code == 200
        data = r.json()
        assert data["job_id"] == "good-job"
        assert data["status"] == "queued"
        _JOBS.pop("good-job", None)

    def test_get_failed_job_status_includes_error(self):
        from ocr_routes import _JOBS
        user = _make_supabase_user(uid="uid-abc")
        app.dependency_overrides[_deps_module.get_current_user] = _ocr_auth_override(user)
        _JOBS["failed-job"] = {
            "status": "failed",
            "owner": "uid-abc",
            "created_at": "2026-01-01T00:00:00Z",
            "error": "OCR service unavailable",
        }
        r = client.get("/api/v1/ocr/jobs/failed-job")
        assert r.status_code == 200
        assert r.json()["error"] == "OCR service unavailable"
        _JOBS.pop("failed-job", None)

    def test_backend_retries_silent_empty_llm_output(self):
        from ocr_routes import _require_llm_extraction

        ocr = MagicMock()
        ocr._merge_fields.return_value = {
            "brand": "Fallback Brand",
            "product_name": None,
            "net_quantity": "500 g",
        }
        final = {
            "product_id": "old-id",
            "views": {
                "front": {
                    "extraction_method": "llm",
                    "ocr_lines": [{"text": "Fallback Brand 500 g"}],
                    "fields": {"brand": None, "net_quantity": None},
                }
            },
            "merged_fields": {"brand": None},
        }

        with patch(
            "ocr_routes.extract_fields_with_llm",
            return_value={"brand": "Fallback Brand", "net_quantity": "500 g"},
        ), patch("ocr_routes.generate_product_id", return_value="fallback-brand-500-g"):
            affected = _require_llm_extraction(ocr, final)

        assert affected == ["front"]
        assert final["views"]["front"]["extraction_method"] == "llm_retry"
        assert final["merged_fields"]["brand"] == "Fallback Brand"
        assert final["product_id"] == "fallback-brand-500-g"

    def test_backend_does_not_retry_valid_llm_fields(self):
        from ocr_routes import _require_llm_extraction

        ocr = MagicMock()
        final = {
            "views": {
                "front": {
                    "extraction_method": "llm",
                    "ocr_lines": [{"text": "Valid Brand"}],
                    "fields": {"brand": "Valid Brand"},
                }
            }
        }

        assert _require_llm_extraction(ocr, final) == []
        ocr._merge_fields.assert_not_called()

    def test_backend_rejects_empty_llm_retry(self):
        from ocr_routes import _require_llm_extraction

        final = {
            "views": {
                "front": {
                    "extraction_method": "rules",
                    "ocr_lines": [{"text": "Visible label text"}],
                    "fields": {"brand": None},
                }
            }
        }
        with patch("ocr_routes.extract_fields_with_llm", return_value={"brand": None}):
            with pytest.raises(RuntimeError, match="No compliance score"):
                _require_llm_extraction(MagicMock(), final)

    def test_backend_rejects_empty_ocr_before_rule_engine_runs(self):
        from ocr_routes import _require_usable_ocr

        final = {
            "views": {
                "front": {"error": "OCR model was unavailable"},
                "back": {"ocr_lines": []},
            },
            "merged_fields": {"brand": None},
        }

        with pytest.raises(RuntimeError, match="OCR could not read text"):
            _require_usable_ocr(final)

    def test_get_past_records_authenticated(self):
        user = _make_supabase_user(uid="uid-abc", email="officer@test.gov.in")
        user.user_metadata = {"officer_id": "OFC-TEST"}
        app.dependency_overrides[_deps_module.get_current_user] = _ocr_auth_override(user)
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = [{"id": "rec-1", "is_compliant": True, "confidence_score": 95.0}]
        mock_client.table.return_value.select.return_value.order.return_value.or_.return_value.limit.return_value.execute.return_value = mock_resp
        with patch("ocr_routes.supabase_client", return_value=mock_client):
            r = client.get("/api/v1/ocr/records")
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["id"] == "rec-1"



# ===========================================================================
# JSON API for React Frontend (/api/me, /api/login, /api/register, /api/logout)
# ===========================================================================

class TestJsonAuthApi:
    def test_api_me_unauthenticated_returns_401(self):
        with patch("app.current_user", return_value=None):
            r = client.get("/api/me")
        assert r.status_code == 401
        assert r.json() == {"detail": "Not authenticated"}

    def test_api_me_authenticated_returns_user_email(self):
        with patch("app.current_user", return_value=_make_supabase_user(email="officer@domain.com")):
            r = client.get("/api/me")
        assert r.status_code == 200
        assert r.json() == {"email": "officer@domain.com"}

    def test_api_login_missing_fields_returns_400(self):
        r = client.post("/api/login", json={"officer_id": "", "password": ""})
        assert r.status_code == 400
        assert "required" in r.json()["error"]

    def test_api_login_officer_not_found_returns_401(self):
        with patch("app._resolve_email", return_value=None):
            r = client.post("/api/login", json={"officer_id": "GHOST-999", "password": "pass"})
        assert r.status_code == 401
        assert "No account found" in r.json()["error"]

    def test_api_login_invalid_credentials_returns_401(self):
        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
        with patch("app._resolve_email", return_value="officer@example.com"), \
             patch("app.supabase_client", return_value=mock_client):
            r = client.post("/api/login", json={"officer_id": "OFC-101", "password": "wrong"})
        assert r.status_code == 401
        assert "Invalid login" in r.json()["error"]

    def test_api_login_success_sets_cookies_and_returns_email(self):
        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.return_value = _make_supabase_session()
        with patch("app._resolve_email", return_value="officer@example.com"), \
             patch("app.supabase_client", return_value=mock_client):
            r = client.post("/api/login", json={"officer_id": "OFC-101", "password": "password123"})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        # email should be the resolved email, not the officer_id string
        assert data["email"] == "officer@example.com"
        assert data["officer_id"] == "OFC-101"
        raw = " ".join(r.headers.get_list("set-cookie"))
        assert ACCESS_COOKIE in raw
        assert REFRESH_COOKIE in raw

    def test_api_register_missing_fields_returns_400(self):
        r = client.post(
            "/api/register",
            json={"email": "a@b.com", "password": "pass1", "confirm_password": "pass1"},
        )
        assert r.status_code == 400
        assert "required" in r.json()["error"]

    def test_api_register_mismatched_password_returns_400(self):
        r = client.post(
            "/api/register",
            json={
                "full_name": "Test Officer",
                "officer_id": "OFC-102",
                "email": "ofc@domain.gov.in",
                "password": "pass1",
                "confirm_password": "pass2",
                "department": "Legal Metrology",
                "role": "inspector",
            },
        )
        assert r.status_code == 400
        assert "match" in r.json()["error"]

    def test_api_register_short_password_returns_400(self):
        r = client.post(
            "/api/register",
            json={
                "full_name": "Test Officer",
                "officer_id": "OFC-102",
                "email": "ofc@domain.gov.in",
                "password": "123",
                "confirm_password": "123",
                "department": "Legal Metrology",
                "role": "inspector",
            },
        )
        assert r.status_code == 400
        assert "6 characters" in r.json()["error"]

    def test_api_register_success_with_session_returns_email_and_cookies(self):
        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.return_value = MagicMock(data={"success": True})
        mock_client.auth.sign_in_with_password.return_value = _make_supabase_session()
        with patch("app.supabase_client", return_value=mock_client):
            r = client.post(
                "/api/register",
                json={
                    "full_name": "Test Officer",
                    "officer_id": "OFC-102",
                    "email": "ofc@domain.gov.in",
                    "password": "password123",
                    "confirm_password": "password123",
                    "department": "Legal Metrology",
                    "role": "inspector",
                },
            )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["email"] == "ofc@domain.gov.in"
        assert data["officer_id"] == "OFC-102"
        raw = " ".join(r.headers.get_list("set-cookie"))
        assert ACCESS_COOKIE in raw

    def test_api_register_rpc_error_returns_400(self):
        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.return_value = MagicMock(data={"error": "User with this email already exists."})
        with patch("app.supabase_client", return_value=mock_client):
            r = client.post(
                "/api/register",
                json={
                    "full_name": "Test Officer",
                    "officer_id": "OFC-103",
                    "email": "ofc103@domain.gov.in",
                    "password": "password123",
                    "confirm_password": "password123",
                    "department": "Legal Metrology",
                    "role": "inspector",
                },
            )
        assert r.status_code == 400
        assert "already exists" in r.json()["error"]

    def test_api_logout_clears_cookies(self):
        mock_client = MagicMock()
        with patch("app.supabase_client", return_value=mock_client):
            r = client.post(
                "/api/logout",
                cookies={ACCESS_COOKIE: "tok", REFRESH_COOKIE: "ref"},
            )
        assert r.status_code == 200
        assert r.json() == {"success": True}
        raw = " ".join(r.headers.get_list("set-cookie"))
        assert ACCESS_COOKIE in raw
        assert REFRESH_COOKIE in raw

    def test_api_forgot_password_missing_officer_id_returns_400(self):
        r = client.post("/api/forgot-password", json={"officer_id": ""})
        assert r.status_code == 400
        assert "required" in r.json()["error"]

    def test_api_forgot_password_officer_not_found_returns_404(self):
        with patch("app._resolve_email", return_value=None):
            r = client.post("/api/forgot-password", json={"officer_id": "UNKNOWN-99"})
        assert r.status_code == 404
        assert "No account found" in r.json()["error"]

    def test_api_forgot_password_success_returns_200(self):
        mock_client = MagicMock()
        mock_client.auth.reset_password_email.return_value = None
        with patch("app._resolve_email", return_value="officer@example.com"), \
             patch("app.supabase_client", return_value=mock_client):
            r = client.post("/api/forgot-password", json={"officer_id": "OFC-001"})
        assert r.status_code == 200
        assert r.json()["success"] is True
        mock_client.auth.reset_password_email.assert_called_once_with("officer@example.com")

    def test_api_forgot_password_supabase_error_returns_500(self):
        mock_client = MagicMock()
        mock_client.auth.reset_password_email.side_effect = Exception("Rate limit reached")
        with patch("app._resolve_email", return_value="officer@example.com"), \
             patch("app.supabase_client", return_value=mock_client):
            r = client.post("/api/forgot-password", json={"officer_id": "OFC-001"})
        assert r.status_code == 500
        assert "Rate limit" in r.json()["error"]
