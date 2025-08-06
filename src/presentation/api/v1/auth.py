"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from ....application.services import JwtService
from ....application.use_cases.auth import (
    LoginUseCase,
    LogoutUseCase,
    RefreshTokenUseCase,
    RegisterUserUseCase,
)
from ....application.use_cases.auth.login_use_case import LoginInput
from ....application.use_cases.auth.logout_use_case import LogoutInput
from ....application.use_cases.auth.refresh_token_use_case import RefreshTokenInput
from ....application.use_cases.auth.register_user_use_case import RegisterUserInput
from ....domain.exceptions.auth_exceptions import (
    AuthenticationException,
    SessionNotFoundException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from ....domain.repositories import SessionRepository, UserRepository
from ....infrastructure.config.settings import get_settings
from ....infrastructure.database import get_session_repository, get_user_repository
from ..dependencies.auth import RequireAuth

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


# Request/Response models
class LoginRequest(BaseModel):
    """Login request model."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class LoginResponse(BaseModel):
    """Login response model."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class RegisterRequest(BaseModel):
    """User registration request model."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")


class RegisterResponse(BaseModel):
    """User registration response model."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    role: str = Field(..., description="User role")
    created_at: str = Field(..., description="Account creation timestamp")


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""

    refresh_token: str = Field(..., description="JWT refresh token")


class RefreshTokenResponse(BaseModel):
    """Refresh token response model."""

    access_token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class UserInfoResponse(BaseModel):
    """Current user information response model."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")
    is_email_verified: bool = Field(..., description="Whether email is verified")
    created_at: str = Field(..., description="Account creation timestamp")
    last_login_at: str | None = Field(None, description="Last login timestamp")


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    req: Request,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
) -> LoginResponse:
    """Authenticate user and return JWT tokens.

    Args:
        request: Login credentials
        req: FastAPI request object for IP/user agent
        user_repository: User repository
        session_repository: Session repository

    Returns:
        JWT tokens and metadata

    Raises:
        HTTPException: 401 if authentication fails
    """
    settings = get_settings()
    jwt_service = JwtService(settings)
    use_case = LoginUseCase(user_repository, session_repository, jwt_service)

    try:
        result = await use_case.execute(
            LoginInput(
                email=request.email,
                password=request.password,
                ip_address=req.client.host if req.client else None,
                user_agent=req.headers.get("user-agent"),
            )
        )
        return LoginResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )
    except (AuthenticationException, UserNotFoundException) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    request: RegisterRequest,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> RegisterResponse:
    """Register a new user account.

    Args:
        request: Registration data
        user_repository: User repository

    Returns:
        Created user information

    Raises:
        HTTPException: 400 if user already exists or validation fails
    """
    use_case = RegisterUserUseCase(user_repository)

    try:
        result = await use_case.execute(
            RegisterUserInput(
                email=request.email,
                password=request.password,
                name=request.name,
                role="viewer",  # Default role for new users
            )
        )
        return RegisterResponse(
            id=str(result.user.id),
            email=result.user.email.value,
            name=result.user.name,
            role=result.user.role.name.value,
            created_at=result.user.created_at.isoformat(),
        )
    except UserAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    req: Request,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
) -> RefreshTokenResponse:
    """Refresh access token using refresh token.

    Args:
        request: Refresh token
        req: FastAPI request object for IP/user agent
        user_repository: User repository
        session_repository: Session repository

    Returns:
        New JWT tokens

    Raises:
        HTTPException: 401 if refresh token is invalid
    """
    settings = get_settings()
    jwt_service = JwtService(settings)
    use_case = RefreshTokenUseCase(session_repository, user_repository, jwt_service)

    try:
        result = await use_case.execute(
            RefreshTokenInput(
                refresh_token=request.refresh_token,
                ip_address=req.client.host if req.client else None,
                user_agent=req.headers.get("user-agent"),
            )
        )
        return RefreshTokenResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )
    except (AuthenticationException, SessionNotFoundException) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: RequireAuth,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> None:
    """Logout current session.

    Args:
        current_user: Current authenticated user
        session_repository: Session repository
        credentials: Bearer token credentials

    Returns:
        None (204 No Content)
    """
    use_case = LogoutUseCase(session_repository)

    await use_case.execute(
        LogoutInput(
            user_id=current_user.id,
            access_token=credentials.credentials,
        )
    )


@router.post("/logout/all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all_sessions(
    current_user: RequireAuth,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
) -> None:
    """Logout all sessions for current user.

    Args:
        current_user: Current authenticated user
        session_repository: Session repository

    Returns:
        None (204 No Content)
    """
    use_case = LogoutUseCase(session_repository)

    await use_case.execute(
        LogoutInput(
            user_id=current_user.id,
            session_id=None,  # None means logout all sessions
        )
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: RequireAuth,
) -> UserInfoResponse:
    """Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        User information
    """
    return UserInfoResponse(
        id=str(current_user.id),
        email=current_user.email.value,
        name=current_user.name,
        role=current_user.role.name.value,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        created_at=current_user.created_at.isoformat(),
        last_login_at=(
            current_user.last_login_at.isoformat()
            if current_user.last_login_at
            else None
        ),
    )
