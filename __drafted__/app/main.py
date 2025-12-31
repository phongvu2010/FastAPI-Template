from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from .core.module_loader import discover_modules
from .core.user_registry import user_registry


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


def load_app_modules(app):
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

        # 3. Automatically mount each module's static.
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


load_app_modules(app)


@app.get("/error", response_class=HTMLResponse, name="error_page")
async def error_page(
    request: Request,
    error_message: str = "An Error Occurred",
    detail: Optional[str] = "The requested resource could not be loaded.",
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
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


@app.get("/health", response_class=HTMLResponse)
async def health(request: Request):
    """
    Basic endpoint for testing an application.
    """
    current_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS]

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{request.app.title}</title>
    </head>
    <body>
        <h1>Chào mừng đến với {request.app.title}!</h1>
        <p>Phiên bản: {request.app.version}</p>
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
