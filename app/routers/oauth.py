from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routers.auth import ACCESS_TOKEN_EXPIRE_MINUTES, COOKIE_SECURE, create_access_token

router = APIRouter(prefix="/api/auth", tags=["oauth"])

# ---------------------------------------------------------------------------
# Authlib OAuth client — providers are registered only when their credentials
# are present in the environment so the app starts cleanly without them.
# ---------------------------------------------------------------------------

try:
    from authlib.integrations.starlette_client import OAuth
    from starlette.config import Config

    _config = Config(".env")
    oauth = OAuth(_config)

    if os.getenv("GOOGLE_CLIENT_ID"):
        oauth.register(
            name="google",
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    if os.getenv("MICROSOFT_CLIENT_ID"):
        oauth.register(
            name="microsoft",
            client_id=os.getenv("MICROSOFT_CLIENT_ID"),
            client_secret=os.getenv("MICROSOFT_CLIENT_SECRET"),
            server_metadata_url=(
                f"https://login.microsoftonline.com/"
                f"{os.getenv('MICROSOFT_TENANT_ID', 'common')}"
                f"/v2.0/.well-known/openid-configuration"
            ),
            client_kwargs={"scope": "openid email profile"},
        )

    _oauth_available = True
except ImportError:
    _oauth_available = False


def _require_oauth():
    if not _oauth_available:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OAuth dependencies are not installed.",
        )


def _get_or_create_user(db: Session, email: str) -> User:
    """Look up a user by email; create an OAuth-only account if not found."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, hashed_password=None)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------

@router.get("/google", summary="Initiate Google OAuth sign-in")
async def google_login(request: Request):
    _require_oauth()
    if not os.getenv("GOOGLE_CLIENT_ID"):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google OAuth is not configured.")
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback", include_in_schema=False)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    _require_oauth()
    token = await oauth.google.authorize_access_token(request)
    email = token["userinfo"]["email"]
    user = _get_or_create_user(db, email)
    access_token = create_access_token(user.email)
    response = RedirectResponse(url="/portal.html")
    response.set_cookie(
        key="andel_token", value=access_token, httponly=True, samesite="strict",
        secure=COOKIE_SECURE, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/",
    )
    return response


# ---------------------------------------------------------------------------
# Microsoft
# ---------------------------------------------------------------------------

@router.get("/microsoft", summary="Initiate Microsoft OAuth sign-in")
async def microsoft_login(request: Request):
    _require_oauth()
    if not os.getenv("MICROSOFT_CLIENT_ID"):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Microsoft OAuth is not configured.")
    redirect_uri = request.url_for("microsoft_callback")
    return await oauth.microsoft.authorize_redirect(request, redirect_uri)


@router.get("/microsoft/callback", name="microsoft_callback", include_in_schema=False)
async def microsoft_callback(request: Request, db: Session = Depends(get_db)):
    _require_oauth()
    token = await oauth.microsoft.authorize_access_token(request)
    userinfo = token.get("userinfo") or token.get("id_token_claims") or {}
    email = userinfo.get("email") or userinfo.get("preferred_username")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not retrieve email from Microsoft.")
    user = _get_or_create_user(db, email)
    access_token = create_access_token(user.email)
    response = RedirectResponse(url="/portal.html")
    response.set_cookie(
        key="andel_token", value=access_token, httponly=True, samesite="strict",
        secure=COOKIE_SECURE, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/",
    )
    return response
