from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ....core.config import settings

router = APIRouter(tags=["utils"])


@router.get("/health", response_class=HTMLResponse)
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
