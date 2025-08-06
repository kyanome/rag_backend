"""Authentication dependencies for FastAPI."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError  # type: ignore[import-untyped]

from ....application.services import JwtService
from ....domain.entities import User
from ....domain.exceptions.auth_exceptions import UserNotFoundException
from ....domain.repositories import UserRepository
from ....domain.value_objects import Permission, UserId, UserRole
from ....infrastructure.config.settings import get_settings
from ....infrastructure.database import get_user_repository

# Security scheme for JWT Bearer tokens
security = HTTPBearer()


async def get_jwt_service() -> JwtService:
    """Get JWT service instance."""
    settings = get_settings()
    return JwtService(settings)


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: Annotated[JwtService, Depends(get_jwt_service)],
) -> UserId:
    """Extract and validate user ID from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        jwt_service: JWT service instance

    Returns:
        User ID from token

    Raises:
        HTTPException: If token is invalid or user ID cannot be extracted
    """
    token = credentials.credentials
    try:
        # Verify it's an access token and extract user ID
        payload = jwt_service.verify_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return UserId(user_id_str)
    except (JWTError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    user_id: Annotated[UserId, Depends(get_current_user_id)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    """Get current authenticated user.

    Args:
        user_id: User ID from token
        user_repository: User repository instance

    Returns:
        Current user entity

    Raises:
        HTTPException: If user not found or not active
    """
    try:
        user = await user_repository.find_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is not active",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except UserNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User not found: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# Convenience dependencies for common use cases
RequireAuth = Annotated[User, Depends(get_current_user)]


def require_auth() -> type[RequireAuth]:
    """Require authentication for an endpoint.

    Usage:
        @router.get("/protected")
        async def protected_endpoint(current_user: Annotated[User, Depends(require_auth())]):
            return {"user": current_user.email.value}
    """
    return RequireAuth


def require_role(role: UserRole | list[UserRole]) -> Callable:
    """Require specific role(s) for an endpoint.

    Args:
        role: Single role or list of allowed roles

    Usage:
        @router.get("/admin")
        async def admin_endpoint(current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))]):
            return {"admin": True}
    """
    allowed_roles = [role] if isinstance(role, UserRole) else role

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {[r.name.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


def require_permission(permission: Permission | list[Permission]) -> Callable:
    """Require specific permission(s) for an endpoint.

    Args:
        permission: Single permission or list of required permissions

    Usage:
        @router.delete("/documents/{id}")
        async def delete_document(
            current_user: Annotated[User, Depends(require_permission(Permission.DOCUMENT_DELETE))]
        ):
            return {"deleted": True}
    """
    required_permissions = (
        [permission] if isinstance(permission, Permission) else permission
    )

    async def permission_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        user_permissions = current_user.role.permissions
        if not all(perm in user_permissions for perm in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {[p.value for p in required_permissions]}",
            )
        return current_user

    return permission_checker
