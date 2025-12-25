# uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --workers 4
# fastapi run app/main.py --host 0.0.0.0 --port 8000 --reload --workers 4

import logging
# import sentry_sdk

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from .modules.auth.routers import auth, users

from .core.deps import NotAuthenticatedWebException
from .web import utils
from .core.config import settings
from .web import views

# Setup logging
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# SENTRY CONFIGURATION (Optional)
# -----------------------------------------------------------------------

# if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
#     sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


# -----------------------------------------------------------------------
# CSRF CONFIGURATION
# -----------------------------------------------------------------------

@CsrfProtect.load_config
def load_csrf_config():
    """
    Loads CSRF configuration.
    """
    return [
        ("secret_key", settings.CSRF_SECRET_KEY),
        ("cookie_name", "csrf_token"),
        ("cookie_samesite", "lax"),
        ("cookie_secure", settings.COOKIE_SECURE),
        ("cookie_path", "/"),
    ]


# -----------------------------------------------------------------------
# APP INITIALIZATION
# -----------------------------------------------------------------------

def custom_generate_unique_id(route: APIRoute) -> str:
    """
    Generates unique operation IDs for OpenAPI.
    """
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

# -----------------------------------------------------------------------
# MIDDLEWARE
# -----------------------------------------------------------------------

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Static files serving (e.g., CSS, JS, Images)
app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------------------------------------------------------------
# EXCEPTION HANDLERS
# -----------------------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Redirects web errors to HTML page, API errors to JSON.
    """
    if exc.status_code == status.HTTP_404_NOT_FOUND and not request.url.path.startswith(settings.API_V1_STR):
        base_url = request.url_for("error_page")
        error_url = f"{base_url}?title=Page Not Found&detail=Resource does not exist.&status_code={exc.status_code}"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    """
    Handles CSRF errors and returns a 400 Bad Request response.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": f"CSRF Error: {exc.message}"},
    )


@app.exception_handler(NotAuthenticatedWebException)
async def auth_exception_redirect_handler(
    request: Request, exc: NotAuthenticatedWebException
):
    """
    Redirects unauthenticated web requests to login.
    """
    return RedirectResponse(
        url=request.url_for("login_page"),
        status_code=status.HTTP_302_FOUND,
    )


# -----------------------------------------------------------------------
# ROUTERS
# -----------------------------------------------------------------------

# Router for JSON APIs
# app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
# app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(utils.router, prefix=settings.API_V1_STR)

# Router for HTML/Web (HTMX)
# Note: Web routes should generally not have the API prefix
app.include_router(views.router)
