"""Integration tests for UserRepository implementation."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import User
from src.domain.exceptions import RepositoryError
from src.domain.exceptions.auth_exceptions import UserNotFoundException
from src.domain.services import PasswordHasher
from src.domain.value_objects import Email, UserId, UserRole
from src.infrastructure.repositories import UserRepositoryImpl


@pytest.fixture
def password_hasher() -> PasswordHasher:
    """Create a password hasher."""
    return PasswordHasher()


@pytest.fixture
def sample_user(password_hasher: PasswordHasher) -> User:
    """Create a sample user."""
    return User(
        id=UserId(value=str(uuid.uuid4())),
        email=Email(value="test@example.com"),
        hashed_password=password_hasher.hash_password("Password123!"),
        name="Test User",
        role=UserRole.viewer(),
        is_active=True,
        is_email_verified=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
async def user_repository(db_session: AsyncSession) -> UserRepositoryImpl:
    """Create a user repository instance."""
    return UserRepositoryImpl(session=db_session)


class TestUserRepositoryIntegration:
    """Integration tests for UserRepository."""

    @pytest.mark.asyncio
    async def test_save_and_find_by_id(
        self,
        user_repository: UserRepositoryImpl,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test saving a user and finding by ID."""
        # Save user
        await user_repository.save(sample_user)
        await db_session.commit()

        # Find by ID
        found_user = await user_repository.find_by_id(sample_user.id)
        assert found_user is not None
        assert found_user.id == sample_user.id
        assert found_user.email == sample_user.email
        assert found_user.role.name == sample_user.role.name
        assert found_user.is_active == sample_user.is_active

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(
        self, user_repository: UserRepositoryImpl
    ) -> None:
        """Test finding a user by ID that doesn't exist."""
        non_existent_id = UserId(value=str(uuid.uuid4()))
        found_user = await user_repository.find_by_id(non_existent_id)
        assert found_user is None

    @pytest.mark.asyncio
    async def test_find_by_email(
        self,
        user_repository: UserRepositoryImpl,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test finding a user by email."""
        # Save user
        await user_repository.save(sample_user)
        await db_session.commit()

        # Find by email
        found_user = await user_repository.find_by_email(sample_user.email)
        assert found_user is not None
        assert found_user.id == sample_user.id
        assert found_user.email == sample_user.email

    @pytest.mark.asyncio
    async def test_find_by_email_not_found(
        self, user_repository: UserRepositoryImpl
    ) -> None:
        """Test finding a user by email that doesn't exist."""
        non_existent_email = Email(value="nonexistent@example.com")
        found_user = await user_repository.find_by_email(non_existent_email)
        assert found_user is None

    @pytest.mark.asyncio
    async def test_save_duplicate_email(
        self,
        user_repository: UserRepositoryImpl,
        sample_user: User,
        password_hasher: PasswordHasher,
        db_session: AsyncSession,
    ) -> None:
        """Test saving a user with duplicate email."""
        # Save first user
        await user_repository.save(sample_user)
        await db_session.commit()

        # Try to save second user with same email
        duplicate_user = User(
            id=UserId(value=str(uuid.uuid4())),
            email=sample_user.email,  # Same email
            hashed_password=password_hasher.hash_password("DifferentPassword123!"),
            name="Duplicate User",
            role=UserRole.editor(),
        )

        with pytest.raises(RepositoryError) as exc_info:
            await user_repository.save(duplicate_user)
            await db_session.commit()

        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_user(
        self,
        user_repository: UserRepositoryImpl,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test updating a user."""
        # Save user
        await user_repository.save(sample_user)
        await db_session.commit()

        # Update user
        sample_user.update_role(UserRole.editor())
        sample_user.verify_email()
        await user_repository.update(sample_user)
        await db_session.commit()

        # Verify update
        updated_user = await user_repository.find_by_id(sample_user.id)
        assert updated_user is not None
        assert updated_user.role.name.value == "editor"
        assert updated_user.is_email_verified is True

    @pytest.mark.asyncio
    async def test_update_nonexistent_user(
        self,
        user_repository: UserRepositoryImpl,
        sample_user: User,
    ) -> None:
        """Test updating a user that doesn't exist."""
        with pytest.raises(UserNotFoundException):
            await user_repository.update(sample_user)

    @pytest.mark.asyncio
    async def test_delete_user(
        self,
        user_repository: UserRepositoryImpl,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test deleting a user."""
        # Save user
        await user_repository.save(sample_user)
        await db_session.commit()

        # Delete user
        await user_repository.delete(sample_user.id)
        await db_session.commit()

        # Verify deletion
        found_user = await user_repository.find_by_id(sample_user.id)
        assert found_user is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(
        self, user_repository: UserRepositoryImpl
    ) -> None:
        """Test deleting a user that doesn't exist."""
        non_existent_id = UserId(value=str(uuid.uuid4()))
        with pytest.raises(UserNotFoundException):
            await user_repository.delete(non_existent_id)

    @pytest.mark.asyncio
    async def test_find_all_with_pagination(
        self,
        user_repository: UserRepositoryImpl,
        password_hasher: PasswordHasher,
        db_session: AsyncSession,
    ) -> None:
        """Test finding all users with pagination."""
        # Create multiple users
        users = []
        for i in range(5):
            user = User(
                id=UserId(value=str(uuid.uuid4())),
                email=Email(value=f"user{i}@example.com"),
                hashed_password=password_hasher.hash_password("Password123!"),
                name=f"User {i}",
                role=UserRole.viewer(),
            )
            users.append(user)
            await user_repository.save(user)

        await db_session.commit()

        # Test pagination
        page1 = await user_repository.find_all(skip=0, limit=2)
        assert len(page1) == 2

        page2 = await user_repository.find_all(skip=2, limit=2)
        assert len(page2) == 2

        page3 = await user_repository.find_all(skip=4, limit=2)
        assert len(page3) == 1

        # Verify no duplicates
        all_ids = [u.id.value for u in page1 + page2 + page3]
        assert len(all_ids) == len(set(all_ids))

    @pytest.mark.asyncio
    async def test_find_active_users(
        self,
        user_repository: UserRepositoryImpl,
        password_hasher: PasswordHasher,
        db_session: AsyncSession,
    ) -> None:
        """Test finding only active users."""
        # Create active and inactive users
        active_user = User(
            id=UserId(value=str(uuid.uuid4())),
            email=Email(value="active@example.com"),
            hashed_password=password_hasher.hash_password("Password123!"),
            name="Active User",
            role=UserRole.viewer(),
            is_active=True,
        )
        inactive_user = User(
            id=UserId(value=str(uuid.uuid4())),
            email=Email(value="inactive@example.com"),
            hashed_password=password_hasher.hash_password("Password123!"),
            name="Inactive User",
            role=UserRole.viewer(),
            is_active=False,
        )

        await user_repository.save(active_user)
        await user_repository.save(inactive_user)
        await db_session.commit()

        # Find active users
        active_users = await user_repository.find_active_users()
        assert len(active_users) >= 1
        assert all(u.is_active for u in active_users)
        assert active_user.id.value in [u.id.value for u in active_users]
        assert inactive_user.id.value not in [u.id.value for u in active_users]

    @pytest.mark.asyncio
    async def test_exists_with_email(
        self,
        user_repository: UserRepositoryImpl,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test checking if user exists with email."""
        # Before saving
        exists = await user_repository.exists_with_email(sample_user.email)
        assert exists is False

        # After saving
        await user_repository.save(sample_user)
        await db_session.commit()

        exists = await user_repository.exists_with_email(sample_user.email)
        assert exists is True

    @pytest.mark.asyncio
    async def test_count_users(
        self,
        user_repository: UserRepositoryImpl,
        password_hasher: PasswordHasher,
        db_session: AsyncSession,
    ) -> None:
        """Test counting users."""
        initial_count = await user_repository.count()

        # Add users
        for i in range(3):
            user = User(
                id=UserId(value=str(uuid.uuid4())),
                email=Email(value=f"count{i}@example.com"),
                hashed_password=password_hasher.hash_password("Password123!"),
                name=f"Count User {i}",
                role=UserRole.viewer(),
            )
            await user_repository.save(user)

        await db_session.commit()

        final_count = await user_repository.count()
        assert final_count == initial_count + 3

    @pytest.mark.asyncio
    async def test_count_active_users(
        self,
        user_repository: UserRepositoryImpl,
        password_hasher: PasswordHasher,
        db_session: AsyncSession,
    ) -> None:
        """Test counting active users."""
        initial_count = await user_repository.count_active()

        # Add active and inactive users
        for i in range(2):
            user = User(
                id=UserId(value=str(uuid.uuid4())),
                email=Email(value=f"active{i}@example.com"),
                hashed_password=password_hasher.hash_password("Password123!"),
                name=f"Active Count User {i}",
                role=UserRole.viewer(),
                is_active=True,
            )
            await user_repository.save(user)

        inactive_user = User(
            id=UserId(value=str(uuid.uuid4())),
            email=Email(value="inactive_count@example.com"),
            hashed_password=password_hasher.hash_password("Password123!"),
            name="Inactive Count User",
            role=UserRole.viewer(),
            is_active=False,
        )
        await user_repository.save(inactive_user)
        await db_session.commit()

        final_count = await user_repository.count_active()
        assert final_count == initial_count + 2
