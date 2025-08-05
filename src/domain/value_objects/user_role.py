"""UserRole value object implementation."""

from dataclasses import dataclass
from enum import Enum


class RoleName(str, Enum):
    """Enumeration of available role names."""

    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Enumeration of available permissions."""

    # Document permissions
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"

    # User management permissions
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # System permissions
    SYSTEM_ADMIN = "system:admin"


# Role to permissions mapping
ROLE_PERMISSIONS = {
    RoleName.ADMIN: frozenset(
        {
            Permission.DOCUMENT_CREATE,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_DELETE,
            Permission.USER_CREATE,
            Permission.USER_READ,
            Permission.USER_UPDATE,
            Permission.USER_DELETE,
            Permission.SYSTEM_ADMIN,
        }
    ),
    RoleName.EDITOR: frozenset(
        {
            Permission.DOCUMENT_CREATE,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_DELETE,
            Permission.USER_READ,
        }
    ),
    RoleName.VIEWER: frozenset(
        {
            Permission.DOCUMENT_READ,
            Permission.USER_READ,
        }
    ),
}


@dataclass(frozen=True)
class UserRole:
    """Value object representing a user role with permissions."""

    name: RoleName
    permissions: frozenset[Permission]

    @classmethod
    def from_name(cls, role_name: str) -> "UserRole":
        """Create a UserRole from a role name string."""
        try:
            name = RoleName(role_name.lower())
        except ValueError as e:
            raise ValueError(f"Invalid role name: {role_name}") from e

        permissions = ROLE_PERMISSIONS.get(name, frozenset())
        return cls(name=name, permissions=permissions)

    @classmethod
    def admin(cls) -> "UserRole":
        """Create an admin role."""
        return cls.from_name(RoleName.ADMIN.value)

    @classmethod
    def editor(cls) -> "UserRole":
        """Create an editor role."""
        return cls.from_name(RoleName.EDITOR.value)

    @classmethod
    def viewer(cls) -> "UserRole":
        """Create a viewer role."""
        return cls.from_name(RoleName.VIEWER.value)

    def has_permission(self, permission: Permission) -> bool:
        """Check if the role has a specific permission."""
        return permission in self.permissions

    def can_create_documents(self) -> bool:
        """Check if the role can create documents."""
        return self.has_permission(Permission.DOCUMENT_CREATE)

    def can_read_documents(self) -> bool:
        """Check if the role can read documents."""
        return self.has_permission(Permission.DOCUMENT_READ)

    def can_update_documents(self) -> bool:
        """Check if the role can update documents."""
        return self.has_permission(Permission.DOCUMENT_UPDATE)

    def can_delete_documents(self) -> bool:
        """Check if the role can delete documents."""
        return self.has_permission(Permission.DOCUMENT_DELETE)

    def is_admin(self) -> bool:
        """Check if this is an admin role."""
        return self.name == RoleName.ADMIN

    def __str__(self) -> str:
        """Return string representation."""
        return self.name.value
