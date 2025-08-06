"""Integration tests for authentication API endpoints."""

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services import JwtService
from src.domain.entities import Session, User
from src.domain.services import PasswordHasher
from src.domain.value_objects import Email, UserId, UserRole
from src.infrastructure.repositories import SessionRepositoryImpl, UserRepositoryImpl
from src.presentation.main import app


class TestAuthAPI:
    """Integration tests for authentication API endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def password_hasher(self) -> PasswordHasher:
        """Create a password hasher."""
        return PasswordHasher()

    @pytest.fixture
    def jwt_service(self) -> JwtService:
        """Create a JWT service."""
        return JwtService()

    @pytest.fixture
    async def test_user(
        self, db_session: AsyncSession, password_hasher: PasswordHasher
    ) -> User:
        """Create and save a test user."""
        user = User(
            id=UserId(value=str(uuid.uuid4())),
            email=Email(value="testauth@example.com"),
            hashed_password=password_hasher.hash_password("TestPassword123!"),
            name="Test Auth User",
            role=UserRole.editor(),
            is_active=True,
            is_email_verified=True,
        )

        user_repo = UserRepositoryImpl(session=db_session)
        await user_repo.save(user)
        await db_session.commit()
        return user

    @pytest.fixture
    async def test_session(
        self, db_session: AsyncSession, test_user: User, jwt_service: JwtService
    ) -> Session:
        """Create and save a test session."""
        access_token, _ = jwt_service.create_access_token(
            test_user.id, test_user.email.value, test_user.role
        )
        refresh_token, _ = jwt_service.create_refresh_token(test_user.id)

        session = Session.create(
            user_id=test_user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_ttl=timedelta(minutes=15),
            refresh_token_ttl=timedelta(days=30),
            ip_address="192.168.1.1",
            user_agent="Test Agent",
        )

        session_repo = SessionRepositoryImpl(session=db_session)
        await session_repo.save(session)
        await db_session.commit()
        return session

    @pytest.mark.asyncio
    async def test_register_successful(
        self, client: TestClient, db_session: AsyncSession
    ) -> None:
        """Test successful user registration."""
        # Arrange
        request_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "name": "New User",
        }

        # Act
        response = client.post("/api/v1/auth/register", json=request_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == request_data["email"]
        assert data["name"] == request_data["name"]
        assert data["role"]["name"] == "viewer"  # Default role
        assert "id" in data
        assert "created_at" in data

        # Verify user was saved to database
        user_repo = UserRepositoryImpl(session=db_session)
        saved_user = await user_repo.find_by_email(Email(value=request_data["email"]))
        assert saved_user is not None
        assert saved_user.email.value == request_data["email"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, client: TestClient, test_user: User
    ) -> None:
        """Test registration with duplicate email."""
        # Arrange
        request_data = {
            "email": test_user.email.value,
            "password": "AnotherPassword123!",
            "name": "Duplicate User",
        }

        # Act
        response = client.post("/api/v1/auth/register", json=request_data)

        # Assert
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: TestClient) -> None:
        """Test registration with invalid email format."""
        # Arrange
        request_data = {
            "email": "invalid-email",
            "password": "Password123!",
            "name": "Invalid Email User",
        }

        # Act
        response = client.post("/api/v1/auth/register", json=request_data)

        # Assert
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_successful(
        self, client: TestClient, test_user: User, db_session: AsyncSession
    ) -> None:
        """Test successful login."""
        # Arrange
        request_data = {
            "email": test_user.email.value,
            "password": "TestPassword123!",
        }

        # Act
        response = client.post("/api/v1/auth/login", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_id"] == test_user.id.value
        assert data["email"] == test_user.email.value
        assert data["role"]["name"] == test_user.role.name.value

        # Verify session was created
        session_repo = SessionRepositoryImpl(session=db_session)
        sessions = await session_repo.find_by_user_id(test_user.id)
        assert len(sessions) > 0

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: TestClient) -> None:
        """Test login with invalid credentials."""
        # Arrange
        request_data = {
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!",
        }

        # Act
        response = client.post("/api/v1/auth/login", json=request_data)

        # Assert
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self, client: TestClient, test_user: User
    ) -> None:
        """Test login with wrong password."""
        # Arrange
        request_data = {
            "email": test_user.email.value,
            "password": "WrongPassword123!",
        }

        # Act
        response = client.post("/api/v1/auth/login", json=request_data)

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_successful(
        self, client: TestClient, test_session: Session, db_session: AsyncSession
    ) -> None:
        """Test successful logout."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_session.access_token}"}

        # Act
        response = client.post("/api/v1/auth/logout", headers=headers)

        # Assert
        assert response.status_code == 204

        # Verify session was deleted
        session_repo = SessionRepositoryImpl(session=db_session)
        deleted_session = await session_repo.find_by_id(test_session.id)
        assert deleted_session is None

    @pytest.mark.asyncio
    async def test_logout_invalid_token(self, client: TestClient) -> None:
        """Test logout with invalid token."""
        # Arrange
        headers = {"Authorization": "Bearer invalid_token"}

        # Act
        response = client.post("/api/v1/auth/logout", headers=headers)

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_successful(
        self, client: TestClient, test_session: Session
    ) -> None:
        """Test successful token refresh."""
        # Arrange
        request_data = {"refresh_token": test_session.refresh_token}

        # Act
        response = client.post("/api/v1/auth/refresh", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["refresh_token"] == test_session.refresh_token
        assert data["token_type"] == "bearer"
        # New access token should be different
        assert data["access_token"] != test_session.access_token

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: TestClient) -> None:
        """Test refresh with invalid token."""
        # Arrange
        request_data = {"refresh_token": "invalid_refresh_token"}

        # Act
        response = client.post("/api/v1/auth/refresh", json=request_data)

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_successful(
        self, client: TestClient, test_session: Session, test_user: User
    ) -> None:
        """Test getting current user info."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_session.access_token}"}

        # Act
        response = client.get("/api/v1/auth/me", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id.value
        assert data["email"] == test_user.email.value
        assert data["name"] == test_user.name
        assert data["role"]["name"] == test_user.role.name.value

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: TestClient) -> None:
        """Test getting user info without authentication."""
        # Act
        response = client.get("/api/v1/auth/me")

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: TestClient) -> None:
        """Test getting user info with invalid token."""
        # Arrange
        headers = {"Authorization": "Bearer invalid_token"}

        # Act
        response = client.get("/api/v1/auth/me", headers=headers)

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self,
        client: TestClient,
        db_session: AsyncSession,
        password_hasher: PasswordHasher,
    ) -> None:
        """Test login with inactive user."""
        # Arrange - Create inactive user
        inactive_user = User(
            id=UserId(value=str(uuid.uuid4())),
            email=Email(value="inactive@example.com"),
            hashed_password=password_hasher.hash_password("Password123!"),
            name="Inactive User",
            role=UserRole.viewer(),
            is_active=False,
        )

        user_repo = UserRepositoryImpl(session=db_session)
        await user_repo.save(inactive_user)
        await db_session.commit()

        request_data = {
            "email": inactive_user.email.value,
            "password": "Password123!",
        }

        # Act
        response = client.post("/api/v1/auth/login", json=request_data)

        # Assert
        assert response.status_code == 401
