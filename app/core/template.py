import logging
import os

from fastapi import HTTPException, status, Request, Response
from fastapi.templating import Jinja2Templates
from typing import Optional

# Setup logging
logger = logging.getLogger(__name__)


class NotAuthenticatedWebException(HTTPException):
    """
    Custom exception raised when a web user is not authenticated.
    """
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated for web content",
        )


# -----------------------------------------------------------------------
# TEMPLATE CONFIGURATION
# -----------------------------------------------------------------------
def get_templates():
    """
    Configure Jinja2 to load templates from the root directory 'app/templates'
    AND from the 'templates' directories within each module.
    """
    # 1. Base global templates
    base_template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
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


def render_error_response(
    request: Request,
    error_message: str,
    detail: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    user: Optional[object] = None,
) -> Response:
    """
    Helper to render error page.
    """
    return get_templates().TemplateResponse(
        "error_page.html",
        {
            "request": request,
            "error_message": error_message,
            "detail": detail,
            "user": user,
        },
        status_code=status_code,
    )
