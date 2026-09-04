"""
deps.py – shared FastAPI dependencies for the Label Lens backend.

Extracting the Supabase auth helper here breaks the circular import
between app.py and ocr_routes.py, and lets both modules import
get_current_user without depending on each other.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException, Request, status
from supabase import Client, create_client

load_dotenv(Path(__file__).resolve().parent / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

ACCESS_COOKIE = "sb_access_token"
REFRESH_COOKIE = "sb_refresh_token"


def supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY in backend/.env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_current_user(request: Request):
    """
    FastAPI dependency – reads the Supabase access token from the session
    cookie and returns the authenticated user object.
    Raises HTTP 401 if the cookie is missing or the token is invalid.
    """
    access_token = request.cookies.get(ACCESS_COOKIE)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
        )
    try:
        result = supabase_client().auth.get_user(access_token)
        if result is not None and getattr(result, "user", None) is not None:
            return result.user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please log in again.",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please log in again.",
        )


def current_user_or_none(request: Request):
    """
    Soft version – returns the user if logged in, otherwise None.
    Used by existing HTML routes that redirect instead of raising 401.
    """
    access_token = request.cookies.get(ACCESS_COOKIE)
    if not access_token:
        return None
    try:
        result = supabase_client().auth.get_user(access_token)
        if result is not None and getattr(result, "user", None) is not None:
            return result.user
        return None
    except Exception:
        return None


def auth_error_message(exc: Exception) -> str:
    """Convert a Supabase exception to a human-readable string."""
    message = getattr(exc, "message", None) or str(exc)
    return message or "Something went wrong. Please try again."
