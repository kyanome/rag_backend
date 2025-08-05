"""Integration tests for SessionRepository implementation."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Session, User
from src.domain.exceptions import RepositoryError
from src.domain.exceptions.auth_exceptions import SessionExpiredException
from src.domain.services import PasswordHasher
from src.domain.value_objects import Email, UserId, UserRole
from src.infrastructure.repositories import SessionRepositoryImpl, UserRepositoryImpl
from tests.fixtures.session_fixtures import create_expired_session


@pytest.fixture
def password_hasher() -> PasswordHasher:
    """Create a password hasher."""
    return PasswordHasher()


@pytest.fixture
async def test_user(
    db_session: AsyncSession, password_hasher: PasswordHasher
) -> User:
    """Create and save a test user."""
    user = User(
        id=UserId(value=str(uuid.uuid4())),
        email=Email(value="session_test@example.com"),
        hashed_password=password_hasher.hash_password("Password123!"),
        role=UserRole.viewer(),
        is_active=True,
    )

    user_repo = UserRepositoryImpl(session=db_session)
    await user_repo.save(user)
    await db_session.commit()
    return user


@pytest.fixture
def sample_session(test_user: User) -> Session:
    """Create a sample session."""
    return Session.create(
        user_id=test_user.id,
        access_token="access_token_" + str(uuid.uuid4()),
        refresh_token="refresh_token_" + str(uuid.uuid4()),
        access_token_ttl=timedelta(minutes=15),
        refresh_token_ttl=timedelta(days=30),
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
    )


@pytest.fixture
async def session_repository(db_session: AsyncSession) -> SessionRepositoryImpl:
    """Create a session repository instance."""
    return SessionRepositoryImpl(session=db_session)


class TestSessionRepositoryIntegration:
    """Integration tests for SessionRepository."""

    @pytest.mark.asyncio
    async def test_save_and_find_by_id(
        self,
        session_repository: SessionRepositoryImpl,
        sample_session: Session,
        db_session: AsyncSession,
    ) -> None:
        """Test saving a session and finding by ID."""
        # Save session
        await session_repository.save(sample_session)
        await db_session.commit()

        # Find by ID
        found_session = await session_repository.find_by_id(sample_session.id)
        assert found_session is not None
        assert found_session.id == sample_session.id
        assert found_session.user_id == sample_session.user_id
        assert found_session.access_token == sample_session.access_token
        assert found_session.refresh_token == sample_session.refresh_token

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(
        self, session_repository: SessionRepositoryImpl
    ) -> None:
        """Test finding a session by ID that doesn't exist."""
        non_existent_id = str(uuid.uuid4())
        found_session = await session_repository.find_by_id(non_existent_id)
        assert found_session is None

    @pytest.mark.asyncio
    async def test_find_by_access_token(
        self,
        session_repository: SessionRepositoryImpl,
        sample_session: Session,
        db_session: AsyncSession,
    ) -> None:
        """Test finding a session by access token."""
        # Save session
        await session_repository.save(sample_session)
        await db_session.commit()

        # Find by access token
        found_session = await session_repository.find_by_access_token(
            sample_session.access_token
        )
        assert found_session is not None
        assert found_session.id == sample_session.id
        assert found_session.access_token == sample_session.access_token

    @pytest.mark.asyncio
    async def test_find_by_refresh_token(
        self,
        session_repository: SessionRepositoryImpl,
        sample_session: Session,
        db_session: AsyncSession,
    ) -> None:
        """Test finding a session by refresh token."""
        # Save session
        await session_repository.save(sample_session)
        await db_session.commit()

        # Find by refresh token
        found_session = await session_repository.find_by_refresh_token(
            sample_session.refresh_token
        )
        assert found_session is not None
        assert found_session.id == sample_session.id
        assert found_session.refresh_token == sample_session.refresh_token

    @pytest.mark.asyncio
    async def test_find_by_user_id(
        self,
        session_repository: SessionRepositoryImpl,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test finding all sessions for a user."""
        # Create multiple sessions for the user
        sessions = []
        for i in range(3):
            session = Session.create(
                user_id=test_user.id,
                access_token=f"access_{i}_{uuid.uuid4()}",
                refresh_token=f"refresh_{i}_{uuid.uuid4()}",
            )
            sessions.append(session)
            await session_repository.save(session)

        await db_session.commit()

        # Find by user ID
        found_sessions = await session_repository.find_by_user_id(test_user.id)
        assert len(found_sessions) == 3
        assert all(s.user_id == test_user.id for s in found_sessions)

    @pytest.mark.asyncio
    async def test_update_session(
        self,
        session_repository: SessionRepositoryImpl,
        sample_session: Session,
        db_session: AsyncSession,
    ) -> None:
        """Test updating a session."""
        # Save session
        await session_repository.save(sample_session)
        await db_session.commit()

        # Update session
        new_access_token = "new_access_" + str(uuid.uuid4())
        sample_session.refresh(new_access_token)
        sample_session.update_activity(
            ip_address="192.168.1.2", user_agent="Updated Agent"
        )

        await session_repository.update(sample_session)
        await db_session.commit()

        # Verify update
        updated_session = await session_repository.find_by_id(sample_session.id)
        assert updated_session is not None
        assert updated_session.access_token == new_access_token
        assert updated_session.ip_address == "192.168.1.2"
        assert updated_session.user_agent == "Updated Agent"

    @pytest.mark.asyncio
    async def test_update_expired_session(
        self,
        session_repository: SessionRepositoryImpl,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test updating an expired session."""
        # Create an expired session using fixture
        expired_session = create_expired_session(test_user.id, hours_ago=24)

        await session_repository.save(expired_session)
        await db_session.commit()

        # Try to update expired session
        with pytest.raises(SessionExpiredException):
            await session_repository.update(expired_session)

    @pytest.mark.asyncio
    async def test_delete_session(
        self,
        session_repository: SessionRepositoryImpl,
        sample_session: Session,
        db_session: AsyncSession,
    ) -> None:
        """Test deleting a session."""
        # Save session
        await session_repository.save(sample_session)
        await db_session.commit()

        # Delete session
        await session_repository.delete(sample_session.id)
        await db_session.commit()

        # Verify deletion
        found_session = await session_repository.find_by_id(sample_session.id)
        assert found_session is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(
        self,
        session_repository: SessionRepositoryImpl,
        db_session: AsyncSession,
    ) -> None:
        """Test deleting a session that doesn't exist."""
        non_existent_id = str(uuid.uuid4())
        # Should not raise error
        await session_repository.delete(non_existent_id)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_delete_by_user_id(
        self,
        session_repository: SessionRepositoryImpl,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test deleting all sessions for a user."""
        # Create multiple sessions
        for i in range(3):
            session = Session.create(
                user_id=test_user.id,
                access_token=f"del_access_{i}_{uuid.uuid4()}",
                refresh_token=f"del_refresh_{i}_{uuid.uuid4()}",
            )
            await session_repository.save(session)

        await db_session.commit()

        # Delete all sessions for user
        await session_repository.delete_by_user_id(test_user.id)
        await db_session.commit()

        # Verify deletion
        found_sessions = await session_repository.find_by_user_id(test_user.id)
        assert len(found_sessions) == 0

    @pytest.mark.asyncio
    async def test_delete_expired_sessions(
        self,
        session_repository: SessionRepositoryImpl,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test deleting expired sessions."""
        # Create active and expired sessions
        active_session = Session.create(
            user_id=test_user.id,
            access_token="active_access_" + str(uuid.uuid4()),
            refresh_token="active_refresh_" + str(uuid.uuid4()),
        )
        await session_repository.save(active_session)

        # Create expired sessions
        for i in range(2):
            expired_session = create_expired_session(test_user.id, hours_ago=24 + i)
            await session_repository.save(expired_session)

        await db_session.commit()

        # Delete expired sessions
        deleted_count = await session_repository.delete_expired()
        await db_session.commit()

        assert deleted_count == 2

        # Verify active session still exists
        found_session = await session_repository.find_by_id(active_session.id)
        assert found_session is not None

    @pytest.mark.asyncio
    async def test_count_active_sessions(
        self,
        session_repository: SessionRepositoryImpl,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test counting active sessions."""
        initial_count = await session_repository.count_active()

        # Add active sessions
        for i in range(2):
            session = Session.create(
                user_id=test_user.id,
                access_token=f"count_active_{i}_{uuid.uuid4()}",
                refresh_token=f"count_refresh_{i}_{uuid.uuid4()}",
            )
            await session_repository.save(session)

        # Add expired session
        expired_session = create_expired_session(test_user.id, hours_ago=48)
        await session_repository.save(expired_session)
        await db_session.commit()

        final_count = await session_repository.count_active()
        assert final_count == initial_count + 2

    @pytest.mark.asyncio
    async def test_count_by_user_id(
        self,
        session_repository: SessionRepositoryImpl,
        test_user: User,
        password_hasher: PasswordHasher,
        db_session: AsyncSession,
    ) -> None:
        """Test counting sessions for a specific user."""
        # Create another user
        other_user = User(
            id=UserId(value=str(uuid.uuid4())),
            email=Email(value="other@example.com"),
            hashed_password=password_hasher.hash_password("Password123!"),
            role=UserRole.viewer(),
        )
        user_repo = UserRepositoryImpl(session=db_session)
        await user_repo.save(other_user)

        # Create sessions for both users
        for i in range(3):
            session = Session.create(
                user_id=test_user.id,
                access_token=f"user1_{i}_{uuid.uuid4()}",
                refresh_token=f"user1_refresh_{i}_{uuid.uuid4()}",
            )
            await session_repository.save(session)

        for i in range(2):
            session = Session.create(
                user_id=other_user.id,
                access_token=f"user2_{i}_{uuid.uuid4()}",
                refresh_token=f"user2_refresh_{i}_{uuid.uuid4()}",
            )
            await session_repository.save(session)

        await db_session.commit()

        # Count sessions for each user
        test_user_count = await session_repository.count_by_user_id(test_user.id)
        other_user_count = await session_repository.count_by_user_id(other_user.id)

        assert test_user_count == 3
        assert other_user_count == 2