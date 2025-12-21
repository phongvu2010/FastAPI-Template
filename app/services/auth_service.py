import logging
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import security
from ..core.config import settings
from ..crud import crud_user as crud
from ..models import User, UserCreateInternal, UserRole

logger = logging.getLogger(__name__)


class AuthService:
    """
    Business logic layer for handling Google SSO and authentication.
    """
    @staticmethod
    async def authenticate_google_user(
        db: AsyncSession,
        code: str,
        state_in_request: str,
        state_in_cookie: str,
    ) -> User:
        """
        Authenticates user via Google SSO, performs security checks,
        and creates or updates the user record.
        """
        # 1. CSRF Check
        if state_in_request != state_in_cookie:
            logger.warning(
                f"CSRF State Mismatch: Req={state_in_request}, Cookie={state_in_cookie}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security error: Invalid or missing CSRF state token.",
            )

        # 2. Exchange Code for Token
        try:
            token_data = await security.exchange_code_for_token(code)
        except Exception as e:
            logger.error("Failed to exchange code for token.", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google code exchange failed.",
            )

        # 3. Verify ID Token
        id_token_str = token_data.get("id_token")
        if not id_token_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ID token found in Google response.",
            )

        # Async blocking I/O call
        user_info = await security.get_google_user_info_async(id_token_str)

        google_sub = user_info.get("sub")
        email = user_info.get("email")
        if not google_sub or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google response missing 'sub' or 'email'.",
            )

        # 4. Domain Validation
        if settings.ALLOWED_EMAIL_DOMAINS:
            domain = urlparse(f"http://{email}").netloc.split("@")[-1]
            if domain not in settings.ALLOWED_EMAIL_DOMAINS:
                logger.warning(f"Login rejected for domain: {email}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Email domain '{domain}' is not allowed.",
                )

        # 5. Find or Create User
        user = await crud.get_user_by_google_sub(db, google_sub)
        if not user:
            user_in = UserCreateInternal(
                google_sub=google_sub,
                email=email,
                full_name=user_info.get("name"),
                picture_url=user_info.get("picture"),
            )

            # Determine initial role
            initial_role = UserRole.SENDER
            if settings.INITIAL_ADMIN_EMAIL and email == settings.INITIAL_ADMIN_EMAIL:
                initial_role = UserRole.ADMIN
                user_in.is_active = True
                logger.info(f"User {email} promoted to ADMIN via config.")

            user = await crud.create_user_from_sso(db, user_in, initial_role)

        # 6. Post-login updates
        if user.is_active:
            await crud.update_last_login(db, user)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive. Please contact administrator.",
            )

        return user
