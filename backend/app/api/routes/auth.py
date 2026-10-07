"""Authentication endpoints.

Note what is NOT here: no password hashing, no SQL, no token construction. The
route validates the request body and delegates to AuthService.
"""

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, SessionDep
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: SessionDep) -> TokenResponse:
    return await AuthService(session).register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    return await AuthService(session).login(payload)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: CurrentUser) -> MessageResponse:
    """Logout is client-side for stateless JWTs: the client drops the token.

    This endpoint exists so the frontend has one call to make, and so that a
    server-side token denylist can be added later without changing the client.
    """
    return MessageResponse(message="Logged out. Discard the access token.")
