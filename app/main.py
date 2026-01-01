# uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --workers 4
# fastapi run app/main.py --host 0.0.0.0 --port 8000 --reload --workers 4

import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.exceptions import NotAuthenticatedWebException
from .core.module_loader import discover_modules

# Setup logging
logger = logging.getLogger(__name__)


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
    tag = route.tags[0] if route.tags else "default"
    return f"{tag}-{route.name}"


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


def load_modules(app):
    """
    Automatically scan the app/modules/ directory and register APIRouters.
    Each module must have a 'router.py' file containing the 'router' variable.
    """
    # 1. Discover and load modules (users, documents, v.v...)
    modules = discover_modules(target_submodule="main")

    for module in modules:
        # Get the module name (e.g., 'users' from 'app.modules.users.main')
        try:
            module_parts = module.__name__.split('.')
            module_name = module_parts[-2] 
        except IndexError:
            continue

        # Check if the module has a variable 'routers' before registering it.
        if hasattr(module, "router"):
            app.include_router(module.router)
            logger.info(f"✅ Router connected: `{module_name}`")
        else:
            logger.warning(f"⚠️ Router `{module_name}` is missing a 'router' object in main.py")

        # Automatically mount each module's static.
        module_static_dir = os.path.join("app", "modules", module_name, "static")
        if os.path.exists(module_static_dir):
            # Mount to the URL path: /static/users
            mount_path = f"/static/{module_name}"
            app.mount(mount_path, StaticFiles(directory=module_static_dir), name=f"static_{module_name}")
            logger.info(f"📁 Mounted module static: {mount_path} -> {module_static_dir}")
        else:
            # Log này giúp bạn biết vì sao không load được file js
            logger.debug(f"ℹ️ No static folder found for module: {module_name}")

    # 2. Mount Global Static (For shared CSS/JS)
    global_static_path = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(global_static_path):
        app.mount("/static", StaticFiles(directory=global_static_path), name="static_global")
        logger.info(f"🚀 Mounted Global Static: /static -> {global_static_path}")


# Activate module scanning upon app launch.
load_modules(app)


# -----------------------------------------------------------------------
# ROUTERS HELPER
# -----------------------------------------------------------------------
@app.get("/health", response_class=HTMLResponse)
async def health():
    """
    Basic endpoint for testing an application.
    """
    current_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS]

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{app.title}</title>
    </head>
    <body>
        <h1>Chào mừng đến với {app.title}!</h1>
        <p>Phiên bản: {app.version}</p>
        <p><strong>Origins được phép (từ config):</strong> <code>{current_origins}</code></p>
        <p>Kiểm tra API docs tại: <a href="/docs">/docs</a></p>
        <h2>Trạng thái Router:</h2>
        <ul>
            <li><strong>API Router</strong> được gắn vào <code>{settings.API_V1_STR}</code></li>
            <li><strong>Web/HTMX Router</strong> được gắn vào <code>/</code></li>
        </ul>
    </body>
    </html>
    """
