import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

# Shared auth helpers (supports package and standalone imports)
try:
    from .deps import (
        ACCESS_COOKIE,
        REFRESH_COOKIE,
        supabase_client,
        current_user_or_none as current_user,
        auth_error_message,
    )
    from .ocr_routes import router as ocr_router
except ImportError:
    from deps import (
        ACCESS_COOKIE,
        REFRESH_COOKIE,
        supabase_client,
        current_user_or_none as current_user,
        auth_error_message,
    )
    from ocr_routes import router as ocr_router

app = FastAPI(title="Label Lens Auth")

# CORS – allow the Vite dev server during local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Register OCR API routes
app.include_router(ocr_router)

def set_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    for cookie_name, token in ((ACCESS_COOKIE, access_token), (REFRESH_COOKIE, refresh_token)):
        response.set_cookie(
            key=cookie_name,
            value=token,
            httponly=True,
            samesite="lax",
            secure=False,
            path="/",
            max_age=60 * 60 * 24 * 7,
        )



def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")


def _resolve_email(officer_id: str) -> str | None:
    """Look up the email address associated with a given Officer ID.

    Calls the ``get_email_by_officer_id`` SECURITY DEFINER RPC which has
    access to ``auth.users``.  Returns the email string, or ``None`` if no
    account with that Officer ID exists.
    """
    try:
        res = supabase_client().rpc(
            "get_email_by_officer_id", {"p_officer_id": officer_id}
        ).execute()
        return res.data if isinstance(res.data, str) else None
    except Exception:
        return None


@app.get("/")
def root():
    return {
        "service": "Label Lens API",
        "status": "online",
        "docs": "/docs",
    }



# ── JSON API for the React frontend ──────────────────────────────────────────

@app.get("/api/me")
def api_me(request: Request):
    """Return the current authenticated user as JSON, or 401."""
    user = current_user(request)
    if not user:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    return JSONResponse({"email": user.email})


@app.post("/api/forgot-password")
async def api_forgot_password(request: Request):
    """JSON forgot-password endpoint for the React frontend.
    Accepts {officer_id}.
    Resolves the Officer ID to the registered email and sends a Supabase
    password-reset email.
    """
    body = await request.json()
    officer_id: str = (body.get("officer_id") or "").strip()

    if not officer_id:
        return JSONResponse({"error": "Officer ID is required."}, status_code=400)

    email = _resolve_email(officer_id)
    if not email:
        return JSONResponse(
            {"error": "No account found for that Officer ID."},
            status_code=404,
        )

    try:
        supabase_client().auth.reset_password_email(email)
    except Exception as exc:
        return JSONResponse({"error": auth_error_message(exc)}, status_code=500)

    return JSONResponse({"success": True, "message": "Password reset link sent to your registered email."})



@app.post("/api/login")
async def api_login(request: Request):
    """JSON login endpoint for the React frontend.
    Accepts {officer_id, password}.
    Resolves the Officer ID to the registered email via the
    ``get_email_by_officer_id`` RPC, then authenticates with Supabase.
    Sets HTTP-only session cookies on success.
    """
    body = await request.json()
    officer_id: str = (body.get("officer_id") or "").strip()
    password: str = body.get("password") or ""

    if not officer_id or not password:
        return JSONResponse({"error": "Officer ID and password are required."}, status_code=400)

    # Resolve Officer ID → email
    email = _resolve_email(officer_id)
    if not email:
        return JSONResponse(
            {"error": "No account found for that Officer ID."},
            status_code=401,
        )

    try:
        result = supabase_client().auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:
        return JSONResponse({"error": auth_error_message(exc)}, status_code=401)

    session = result.session
    if not session or not session.access_token:
        return JSONResponse(
            {"error": "Could not start a session. Please try again."},
            status_code=401,
        )

    response = JSONResponse({"success": True, "email": email, "officer_id": officer_id})
    set_session_cookies(response, session.access_token, session.refresh_token)
    return response


@app.post("/api/register")
async def api_register(request: Request):
    """JSON register endpoint for the React frontend.
    Accepts {full_name, officer_id, email, password, confirm_password, department, role}.
    Creates and auto-confirms user without triggering external email rate limits.
    """
    body = await request.json()
    full_name: str = (body.get("full_name") or "").strip()
    officer_id: str = (body.get("officer_id") or "").strip()
    email: str = (body.get("email") or body.get("official_email") or "").strip()
    password: str = body.get("password") or ""
    confirm_password: str = body.get("confirm_password") or ""
    department: str = (body.get("department") or "").strip()
    role: str = (body.get("role") or "").strip()

    if (
        not full_name
        or not officer_id
        or not email
        or not password
        or not department
        or not role
    ):
        return JSONResponse({"error": "All fields are required."}, status_code=400)

    if password != confirm_password:
        return JSONResponse({"error": "Passwords do not match."}, status_code=400)

    if len(password) < 6:
        return JSONResponse(
            {"error": "Password must be at least 6 characters."}, status_code=400
        )

    try:
        client = supabase_client()
        # 1. Create auto-confirmed user account via database RPC
        rpc_res = client.rpc(
            "create_officer_account",
            {
                "p_email": email.strip(),
                "p_password": password,
                "p_officer_id": officer_id.strip(),
                "p_full_name": full_name.strip(),
                "p_department": department.strip(),
                "p_role": role.strip(),
            },
        ).execute()

        rpc_data = rpc_res.data
        if isinstance(rpc_data, dict) and rpc_data.get("error"):
            return JSONResponse({"error": rpc_data["error"]}, status_code=400)

        # 2. Immediately sign in the officer
        login_res = client.auth.sign_in_with_password(
            {"email": email.strip(), "password": password}
        )

        session = login_res.session
        if session and session.access_token:
            response = JSONResponse(
                {"success": True, "email": email, "officer_id": officer_id}
            )
            set_session_cookies(response, session.access_token, session.refresh_token)
            return response

        return JSONResponse(
            {"success": True, "email": email, "officer_id": officer_id}
        )
    except Exception as exc:
        return JSONResponse({"error": auth_error_message(exc)}, status_code=400)


@app.post("/api/logout")
def api_logout(request: Request):
    """JSON logout endpoint for the React frontend."""
    access_token = request.cookies.get(ACCESS_COOKIE)
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    try:
        client = supabase_client()
        if access_token and refresh_token:
            client.auth.set_session(access_token, refresh_token)
        client.auth.sign_out()
    except Exception:
        pass
    response = JSONResponse({"success": True})
    clear_session_cookies(response)
    return response
