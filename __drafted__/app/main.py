import importlib
# import sentry_sdk

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Optional

from .core.user_registry import user_registry


# -----------------------------------------------------------------------
# SENTRY CONFIGURATION (Optional)
# -----------------------------------------------------------------------
# if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
#     sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

# -----------------------------------------------------------------------
# APP INITIALIZATION
# -----------------------------------------------------------------------
app = FastAPI()

# Static files serving (e.g., CSS, JS, Images)
app.mount("/static/users", StaticFiles(directory="app/modules/users/static"), name="static_users")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize global templates variables
templates = Jinja2Templates(directory="templates")


# -----------------------------------------------------------------------
# TEMPLATE CONFIGURATION
# -----------------------------------------------------------------------
def get_templates():
    """
    Configure Jinja2 to load templates from the root directory 'app/templates'
    AND from the 'templates' directories within each module.
    """
    # 1. Base global templates
    base_template_dir = os.path.join(os.path.dirname(__file__), "templates")
    template_dirs = [base_template_dir] if os.path.exists(base_template_dir) else []

    # 2. Scan modules templates (Optional: nếu muốn template nằm trong module)
    modules_path = os.path.join(os.path.dirname(__file__), "modules")
    if os.path.exists(modules_path):
        for module_name in os.listdir(modules_path):
            module_template_dir = os.path.join(modules_path, module_name, "templates")
            if os.path.isdir(module_template_dir):
                template_dirs.append(module_template_dir)

    logger.info(f"🎨 Template directories loaded: {template_dirs}")
    return Jinja2Templates(directory=template_dirs)


# Initialize global templates variables
templates = get_templates()


# -----------------------------------------------------------------------
# EXCEPTION HANDLERS
# -----------------------------------------------------------------------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Redirects web errors to HTML page, API errors to JSON.
    """
    # If it's an API request (based on the path), return JSON.
    if request.url.path.startswith(settings.API_V1_STR):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    # If it's a web request, redirect to the error page.
    # NOTE: Ensure the route 'error_page' exists below.
    return await error_page(
        request=request,
        error_message=f"Lỗi {exc.status_code}",
        detail=exc.detail,
        status_code=exc.status_code,
    )
# @app.exception_handler(StarletteHTTPException)
# async def http_exception_handler(request: Request, exc: StarletteHTTPException):
#     """
#     Redirects web errors to HTML page, API errors to JSON.
#     """
#     try:
#         base_url = request.url_for("error_page")
#         error_url = f"{base_url}?detail={exc.detail}&status_code={exc.status_code}"
#         return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)
#     except Exception:
#         # Fallback if route error_page has not been loaded
#         return HTMLResponse(
#             status_code=exc.status_code,
#             content=f"<h1>Error {exc.status_code}</h1><p>{exc.detail}</p>",
#         )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled system errors (500)
    """
    logger.error(f"Global Error: {str(exc)}", exc_info=True)
    return await error_page(
        request=request,
        error_message="Lỗi hệ thống",
        detail="Đã có lỗi xảy ra phía máy chủ. Vui lòng thử lại sau.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# -----------------------------------------------------------------------
# ROUTERS HELPER
# -----------------------------------------------------------------------
@app.get("/error", response_class=HTMLResponse, name="error_page")
async def error_page(
    request: Request,
    error_message: str = "An Error Occurred",
    detail: Optional[str] = "The requested resource could not be loaded.",
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    user: Optional[object] = None,
):
    """
    Render a system-wide error page.
    Required file: app/templates/error_page.html
    """
    # 1. Tự động lấy user thông qua Registry
    # Nếu module Users chưa load hoặc chưa đăng ký, nó trả về None.
    current_user = await user_registry.get_user_from_request(request)

    return templates.TemplateResponse(
        request=request,
        name="error_page.html",
        context={
            "error_message": error_message,
            "detail": detail,
            "status_code": status_code,
            "user": current_user,
            "settings": settings,
        },
        status_code=status_code,
    )
