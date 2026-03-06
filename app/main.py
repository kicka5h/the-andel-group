import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.database import Base, engine
from app.limiter import limiter
from app.routers import auth, contact, newsletter, oauth

load_dotenv()

# Create tables on startup (use Alembic migrations if you need schema changes later).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Andel Group API",
    description=(
        "REST API for andel.ca — serves the newsletter subscription system "
        "and resident authentication.\n\n"
        "**Interactive docs:** `/docs` (Swagger UI) · `/redoc` (ReDoc)\n\n"
        "All endpoints are prefixed with `/api/`."
    ),
    version="1.0.0",
    contact={"name": "The Andel Group", "email": "info@andel.ca"},
    openapi_tags=[
        {"name": "auth", "description": "Email/password registration and login. Returns signed JWT tokens."},
        {"name": "oauth", "description": "Google and Microsoft OAuth 2.0 sign-in flows."},
        {"name": "newsletter", "description": "Newsletter subscription management — subscribe, unsubscribe, and list."},
        {"name": "contact", "description": "Contact form submissions."},
        {"name": "health", "description": "Server health check."},
    ],
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

allowed_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")
    if o.strip()
]

# SessionMiddleware must be outermost — required by OAuth state parameter handling.
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "change-me-in-production"))

# Trust X-Forwarded-For headers from Apache running on the same machine.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="127.0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(newsletter.router)
app.include_router(contact.router)


@app.get("/api/health", summary="Health check", tags=["health"])
def health():
    return {"status": "ok"}


def _require_localhost(request: Request) -> None:
    """Block access from any host other than localhost."""
    host = request.client.host if request.client else None
    if host not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=403, detail="API documentation is only accessible from the host server.")


@app.get("/openapi.json", include_in_schema=False)
async def openapi_json(request: Request):
    _require_localhost(request)
    return app.openapi()


@app.get("/docs", include_in_schema=False)
async def swagger_ui(request: Request):
    _require_localhost(request)
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Andel Group API — Docs")


@app.get("/redoc", include_in_schema=False)
async def redoc_html(request: Request):
    _require_localhost(request)
    return get_redoc_html(openapi_url="/openapi.json", title="Andel Group API — ReDoc")


# Static files must be mounted last so API routes take priority.
app.mount("/", StaticFiles(directory="static", html=True), name="static")
