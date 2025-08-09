"""Admin API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ....application.use_cases.admin import GetUsersListInput, GetUsersListUseCase
from ....domain.exceptions.auth_exceptions import UserNotFoundException
from ....domain.repositories import UserRepository
from ....domain.value_objects import UserRole
from ....infrastructure.database import get_user_repository
from ..dependencies.auth import require_role

router = APIRouter(prefix="/admin", tags=["Admin"])

# Require admin role for all endpoints
RequireAdmin = Annotated[UserRepository, Depends(require_role(UserRole.ADMIN))]


class UserListResponse(BaseModel):
    """User list response model."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: str = Field(..., description="Account creation timestamp")
    last_login_at: str | None = Field(None, description="Last login timestamp")


class UsersListResponse(BaseModel):
    """Users list response model."""

    users: list[UserListResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    skip: int = Field(..., description="Number of users skipped")
    limit: int = Field(..., description="Maximum number of users returned")


class UpdateUserRoleRequest(BaseModel):
    """Update user role request model."""

    role: str = Field(
        ..., description="New user role", pattern="^(viewer|editor|admin)$"
    )


@router.get("/users", response_model=UsersListResponse)
async def get_users_list(
    _: RequireAdmin,  # Admin authorization check
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    skip: int = 0,
    limit: int = 100,
) -> UsersListResponse:
    """Get list of all users (admin only).

    Args:
        _: Admin authorization dependency
        skip: Number of users to skip
        limit: Maximum number of users to return
        user_repository: User repository

    Returns:
        List of users with pagination

    Raises:
        HTTPException: 403 if not admin
    """
    use_case = GetUsersListUseCase(user_repository)

    result = await use_case.execute(GetUsersListInput(skip=skip, limit=limit))

    return UsersListResponse(
        users=[
            UserListResponse(
                id=str(user.id),
                email=user.email.value,
                name=user.name,
                role=user.role.name.value,
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
                last_login_at=(
                    user.last_login_at.isoformat() if user.last_login_at else None
                ),
            )
            for user in result.users
        ],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.put("/users/{user_id}/role", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    _: RequireAdmin,  # Admin authorization check
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> None:
    """Update user role (admin only).

    Args:
        user_id: User ID to update
        request: New role data
        _: Admin authorization dependency
        user_repository: User repository

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 403 if not admin, 404 if user not found
    """
    try:
        # Find the user
        from ....domain.value_objects import UserId

        target_user = await user_repository.find_by_id(UserId(user_id))
        if not target_user:
            raise UserNotFoundException(f"User {user_id} not found")

        # Update the role
        new_role = UserRole.from_name(request.role)
        target_user.update_role(new_role)

        # Save the updated user
        await user_repository.update(target_user)

    except UserNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {request.role}",
        ) from e


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    _: RequireAdmin,  # Admin authorization check
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> None:
    """Delete user (admin only).

    Args:
        user_id: User ID to delete
        _: Admin authorization dependency
        user_repository: User repository

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 403 if not admin, 404 if user not found
    """
    try:
        from ....domain.value_objects import UserId

        # Check if user exists
        target_user = await user_repository.find_by_id(UserId(user_id))
        if not target_user:
            raise UserNotFoundException(f"User {user_id} not found")

        # Delete the user
        await user_repository.delete(UserId(user_id))

    except UserNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
