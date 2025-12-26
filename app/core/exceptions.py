from fastapi import HTTPException, status


class NotAuthenticatedWebException(HTTPException):
    """
    Custom exception raised when a web user is not authenticated.
    """
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated for web content",
        )
