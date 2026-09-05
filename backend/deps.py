"""
deps.py – shared FastAPI dependencies for the Label Lens backend.

Extracting the Supabase auth helper here breaks the circular import
between app.py and ocr_routes.py, and lets both modules import
get_current_user without depending on each other.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException, Request, Response, status
from supabase import Client, create_client

ENV_FILE = Path(__file__).resolve().parent / ".env"


def _load_runtime_config() -> None:
    """Refresh local configuration without logging sensitive values.

    This lets a long-running development server use values added to
    ``backend/.env`` after it was started. The values remain process-local and
    are never returned by the API.
    """
    load_dotenv(ENV_FILE, override=True)


_load_runtime_config()

ACCESS_COOKIE = "sb_access_token"
REFRESH_COOKIE = "sb_refresh_token"


def supabase_client() -> Client:
    _load_runtime_config()
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY in backend/.env")
    return create_client(supabase_url, supabase_key)


def _write_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    for cookie_name, token in ((ACCESS_COOKIE, access_token), (REFRESH_COOKIE, refresh_token)):
        if not token:
            continue
        response.set_cookie(
            key=cookie_name,
            value=token,
            httponly=True,
            samesite="lax",
            secure=False,
            path="/",
            max_age=60 * 60 * 24 * 7,
        )


def _user_from_access_token(access_token: str):
    result = supabase_client().auth.get_user(access_token)
    if result is not None and getattr(result, "user", None) is not None:
        return result.user
    return None


def get_current_user(request: Request, response: Response):
    """
    FastAPI dependency – reads the Supabase access token from the session
    cookie and returns the authenticated user object.
    Raises HTTP 401 if the cookie is missing or the token is invalid.

    A single failed get_user call during OCR polling used to 401 the
    frontend even though the refresh cookie was still valid. Retry via
    refresh before giving up.
    """
    access_token = request.cookies.get(ACCESS_COOKIE)
    refresh_token = request.cookies.get(REFRESH_COOKIE)

    if access_token:
        try:
            user = _user_from_access_token(access_token)
            if user is not None:
                return user
        except Exception:
            pass

    if refresh_token:
        try:
            refreshed = supabase_client().auth.refresh_session(refresh_token)
            session = getattr(refreshed, "session", None)
            user = getattr(refreshed, "user", None)
            if user is None and session is not None:
                user = getattr(session, "user", None)
            if session is not None and getattr(session, "access_token", None) and user is not None:
                _write_session_cookies(
                    response,
                    session.access_token,
                    getattr(session, "refresh_token", None) or refresh_token,
                )
                return user
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Please log in.",
    )


def current_user_or_none(request: Request):
    """
    Soft version – returns the user if logged in, otherwise None.
    Used by existing HTML routes that redirect instead of raising 401.
    """
    access_token = request.cookies.get(ACCESS_COOKIE)
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if access_token:
        try:
            user = _user_from_access_token(access_token)
            if user is not None:
                return user
        except Exception:
            pass
    if refresh_token:
        try:
            refreshed = supabase_client().auth.refresh_session(refresh_token)
            user = getattr(refreshed, "user", None)
            session = getattr(refreshed, "session", None)
            if user is None and session is not None:
                user = getattr(session, "user", None)
            if user is not None:
                return user
        except Exception:
            pass
    return None


def auth_error_message(exc: Exception) -> str:
    """Convert a Supabase exception to a human-readable string."""
    message = getattr(exc, "message", None) or str(exc)
    return message or "Something went wrong. Please try again."
