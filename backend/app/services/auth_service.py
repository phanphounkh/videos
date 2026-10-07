"""Authentication use cases.

Routes stay thin: they validate input and call these methods. All of the policy
(does the email exist, is the password right, how long is a token valid) lives
here, which is also what makes it unit-testable without HTTP.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse

log = get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def register(self, payload: RegisterRequest) -> TokenResponse:
        email = payload.email.strip().lower()
        if await self.users.email_exists(email):
            # Deliberately explicit: registration cannot be silent about this, or
            # the user can never find out why signup failed.
            raise ConflictError("An account with this email already exists.",
                                code="EMAIL_ALREADY_REGISTERED")

        user = User(
            email=email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        self.users.add(user)
        await self.session.commit()
        log.info("user_registered", user_id=str(user.id))
        return self._token_for(user)

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self.users.get_by_email(payload.email)

        # Same error for "no such user" and "wrong password": revealing which one
        # it was turns the login form into an account-enumeration oracle.
        if user is None or not verify_password(payload.password, user.hashed_password):
            log.info("login_failed", email_domain=payload.email.split("@")[-1])
            raise AuthenticationError("Incorrect email or password.",
                                      code="INVALID_CREDENTIALS")
        if not user.is_active:
            raise AuthenticationError("This account is disabled.", code="ACCOUNT_DISABLED")

        log.info("login_succeeded", user_id=str(user.id))
        return self._token_for(user)

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise AuthenticationError("User no longer exists.", code="INVALID_TOKEN")
        return user

    def _token_for(self, user: User) -> TokenResponse:
        settings = get_settings()
        return TokenResponse(
            access_token=create_access_token(str(user.id), {"email": user.email}),
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(user),
        )
