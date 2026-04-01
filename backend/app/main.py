from http.cookies import SimpleCookie
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import FastAPI, Request as FastAPIRequest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.browser import router as browser_router
from app.api.health import router as health_router
from app.api.insights import router as insights_router
from app.api.labels import router as labels_router
from app.api.plans import router as plans_router
from app.api.runtime import router as runtime_router
from app.api.runs import router as runs_router
from app.adapters.http.api.v1.router import api_router
from app.infrastructure.config import get_settings
from app.infrastructure.lifespan import build_lifespan

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=build_lifespan(settings),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUTH_EXEMPT_PREFIXES = ("/assets", "/health", "/api/health", "/api/v1/health")
AUTH_EXEMPT_PATHS = {"/favicon.ico"}


def _is_auth_exempt(path: str) -> bool:
    if path in AUTH_EXEMPT_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in AUTH_EXEMPT_PREFIXES)


def _build_login_url(request: FastAPIRequest) -> str:
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    forwarded_host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or ""
    ).split(",")[0].strip()
    if forwarded_proto and forwarded_host:
        return_to = f"{forwarded_proto}://{forwarded_host}{request.url.path}"
        if request.url.query:
            return_to = f"{return_to}?{request.url.query}"
    else:
        return_to = str(request.url)
    query = urlencode({"returnTo": return_to})
    return f"{settings.platform_auth_login_url}?{query}"


def _has_platform_cookie(request: FastAPIRequest) -> bool:
    return bool(
        request.cookies.get(settings.platform_auth_cookie_name)
        or request.cookies.get(settings.platform_auth_cookie_fallback_name)
    )


def _validate_platform_session(cookie_header: str) -> bool:
    auth_request = Request(
        settings.platform_auth_session_url,
        headers={
            "accept": "application/json",
            "cookie": cookie_header,
            "user-agent": "social-listening-v3-auth-gateway/1.0",
        },
        method="GET",
    )
    with urlopen(auth_request, timeout=settings.platform_auth_timeout_sec) as response:
        return 200 <= response.status < 300


def _auth_failure_response(request: FastAPIRequest, status_code: int):
    login_url = _build_login_url(request)
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            {
                "detail": "Authentication required" if status_code == 401 else "Authentication service unavailable",
                "login_url": login_url,
            },
            status_code=status_code,
        )
    if status_code == 503:
        return PlainTextResponse("Authentication service unavailable", status_code=503)
    return RedirectResponse(login_url, status_code=307)


@app.middleware("http")
async def require_platform_auth(request: FastAPIRequest, call_next):
    if (
        not settings.platform_auth_enabled
        or request.method == "OPTIONS"
        or _is_auth_exempt(request.url.path)
    ):
        return await call_next(request)

    if not _has_platform_cookie(request):
        return _auth_failure_response(request, 401)

    cookie = SimpleCookie()
    cookie.load(request.headers.get("cookie", ""))
    if not cookie:
        return _auth_failure_response(request, 401)

    try:
        if not _validate_platform_session(request.headers.get("cookie", "")):
            return _auth_failure_response(request, 401)
    except HTTPError as error:
        if error.code in (401, 403):
            return _auth_failure_response(request, 401)
        return _auth_failure_response(request, 503)
    except URLError:
        return _auth_failure_response(request, 503)

    return await call_next(request)

app.include_router(api_router)
app.include_router(browser_router)
app.include_router(health_router)
app.include_router(plans_router)
app.include_router(runs_router)
app.include_router(labels_router)
app.include_router(insights_router)
app.include_router(runtime_router)

static_dir = Path(settings.static_dir)
index_file = static_dir / "index.html"
if index_file.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def frontend_index() -> FileResponse:
        return FileResponse(index_file)
