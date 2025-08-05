"""Tests for UserRole value object."""

import pytest

from src.domain.value_objects import Permission, RoleName, UserRole


class TestUserRole:
    """Test cases for UserRole value object."""

    def test_create_admin_role(self) -> None:
        """Test creating admin role."""
        role = UserRole.admin()

        assert role.name == RoleName.ADMIN
        assert len(role.permissions) == 9  # All permissions
        assert role.is_admin() is True
        assert str(role) == "admin"

    def test_create_editor_role(self) -> None:
        """Test creating editor role."""
        role = UserRole.editor()

        assert role.name == RoleName.EDITOR
        assert len(role.permissions) == 5
        assert role.is_admin() is False
        assert str(role) == "editor"

    def test_create_viewer_role(self) -> None:
        """Test creating viewer role."""
        role = UserRole.viewer()

        assert role.name == RoleName.VIEWER
        assert len(role.permissions) == 2
        assert role.is_admin() is False
        assert str(role) == "viewer"

    def test_from_name_valid(self) -> None:
        """Test creating role from valid name."""
        role = UserRole.from_name("ADMIN")
        assert role.name == RoleName.ADMIN

        role = UserRole.from_name("editor")
        assert role.name == RoleName.EDITOR

        role = UserRole.from_name("VIEWER")
        assert role.name == RoleName.VIEWER

    def test_from_name_invalid(self) -> None:
        """Test creating role from invalid name."""
        with pytest.raises(ValueError, match="Invalid role name"):
            UserRole.from_name("superuser")

    def test_admin_permissions(self) -> None:
        """Test admin role permissions."""
        role = UserRole.admin()

        # Admin should have all permissions
        assert role.can_create_documents() is True
        assert role.can_read_documents() is True
        assert role.can_update_documents() is True
        assert role.can_delete_documents() is True
        assert role.has_permission(Permission.USER_CREATE) is True
        assert role.has_permission(Permission.USER_DELETE) is True
        assert role.has_permission(Permission.SYSTEM_ADMIN) is True

    def test_editor_permissions(self) -> None:
        """Test editor role permissions."""
        role = UserRole.editor()

        # Editor can manage documents but not users
        assert role.can_create_documents() is True
        assert role.can_read_documents() is True
        assert role.can_update_documents() is True
        assert role.can_delete_documents() is True
        assert role.has_permission(Permission.USER_READ) is True
        assert role.has_permission(Permission.USER_CREATE) is False
        assert role.has_permission(Permission.USER_DELETE) is False
        assert role.has_permission(Permission.SYSTEM_ADMIN) is False

    def test_viewer_permissions(self) -> None:
        """Test viewer role permissions."""
        role = UserRole.viewer()

        # Viewer can only read
        assert role.can_create_documents() is False
        assert role.can_read_documents() is True
        assert role.can_update_documents() is False
        assert role.can_delete_documents() is False
        assert role.has_permission(Permission.USER_READ) is True
        assert role.has_permission(Permission.USER_CREATE) is False
        assert role.has_permission(Permission.SYSTEM_ADMIN) is False

    def test_immutability(self) -> None:
        """Test that UserRole is immutable."""
        role = UserRole.admin()

        with pytest.raises(AttributeError):
            role.name = RoleName.VIEWER  # type: ignore

        with pytest.raises(AttributeError):
            role.permissions = frozenset()  # type: ignore

    def test_custom_role_creation(self) -> None:
        """Test creating custom role with specific permissions."""
        custom_permissions = frozenset(
            {
                Permission.DOCUMENT_READ,
                Permission.DOCUMENT_CREATE,
            }
        )
        role = UserRole(name=RoleName.VIEWER, permissions=custom_permissions)

        assert role.name == RoleName.VIEWER
        assert role.permissions == custom_permissions
        assert role.can_read_documents() is True
        assert role.can_create_documents() is True
        assert role.can_update_documents() is False
        assert role.can_delete_documents() is False
