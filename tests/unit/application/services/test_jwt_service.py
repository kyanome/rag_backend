"""Tests for JWT service."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from freezegun import freeze_time
from jose import JWTError, jwt

from src.application.services import JwtService
from src.domain.value_objects import UserId, UserRole
from src.infrastructure.config.settings import Settings


class TestJwtService:
    """Test cases for JWT service."""

    @pytest.fixture
    def settings(self) -> Settings:
        """Create test settings."""
        return Settings()
    
    @pytest.fixture
    def jwt_service(self, settings: Settings) -> JwtService:
        """Create a JWT service instance."""
        return JwtService(settings=settings)

    def test_create_access_token(self, jwt_service: JwtService, settings: Settings) -> None:
        """Test creating an access token."""
        user_id = UserId(value=str(uuid.uuid4()))
        email = "test@example.com"
        role = UserRole.editor()

        token, expiry = jwt_service.create_access_token(user_id, email, role)

        # Verify token structure
        assert isinstance(token, str)
        assert len(token) > 0

        # Verify expiry time
        expected_expiry = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
        assert abs((expiry - expected_expiry).total_seconds()) < 2

        # Decode and verify token payload
        decoded = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        assert decoded["sub"] == str(user_id)
        assert decoded["email"] == email
        assert decoded["role"] == role.name.value
        assert decoded["type"] == "access"
        assert "exp" in decoded
        assert "iat" in decoded

    def test_create_refresh_token(self, jwt_service: JwtService, settings: Settings) -> None:
        """Test creating a refresh token."""
        user_id = UserId(value=str(uuid.uuid4()))
        session_id = str(uuid.uuid4())

        token, expiry = jwt_service.create_refresh_token(user_id, session_id)

        # Verify token structure
        assert isinstance(token, str)
        assert len(token) > 0

        # Verify expiry time
        expected_expiry = datetime.now(UTC) + timedelta(
            days=settings.refresh_token_expire_days
        )
        assert abs((expiry - expected_expiry).total_seconds()) < 2

        # Decode and verify token payload
        decoded = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        assert decoded["sub"] == str(user_id)
        assert decoded["session_id"] == session_id
        assert decoded["type"] == "refresh"
        assert "exp" in decoded
        assert "iat" in decoded

    def test_verify_access_token_valid(self, jwt_service: JwtService) -> None:
        """Test verifying a valid access token."""
        user_id = UserId(value=str(uuid.uuid4()))
        email = "test@example.com"
        role = UserRole.viewer()

        token, _ = jwt_service.create_access_token(user_id, email, role)
        payload = jwt_service.verify_access_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["email"] == email
        assert payload["role"] == role.name.value
        assert payload["type"] == "access"

    def test_verify_access_token_expired(self, jwt_service: JwtService) -> None:
        """Test verifying an expired access token."""
        user_id = UserId(value=str(uuid.uuid4()))
        email = "test@example.com"
        role = UserRole.viewer()

        # Create token in the past
        with freeze_time("2023-01-01"):
            token, _ = jwt_service.create_access_token(user_id, email, role)

        # Verify in the present (expired)
        with pytest.raises(JWTError):
            jwt_service.verify_access_token(token)

    def test_verify_access_token_invalid_signature(
        self, jwt_service: JwtService
    ) -> None:
        """Test verifying a token with invalid signature."""
        # Create a token with a different secret
        payload = {
            "sub": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "viewer",
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=15),
            "iat": datetime.now(UTC),
        }
        invalid_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        with pytest.raises(JWTError):
            jwt_service.verify_access_token(invalid_token)

    def test_verify_access_token_wrong_type(self, jwt_service: JwtService) -> None:
        """Test verifying a refresh token as an access token."""
        user_id = UserId(value=str(uuid.uuid4()))
        session_id = str(uuid.uuid4())
        refresh_token, _ = jwt_service.create_refresh_token(user_id, session_id)

        with pytest.raises(JWTError):
            jwt_service.verify_access_token(refresh_token)

    def test_verify_refresh_token_valid(self, jwt_service: JwtService) -> None:
        """Test verifying a valid refresh token."""
        user_id = UserId(value=str(uuid.uuid4()))
        session_id = str(uuid.uuid4())

        token, _ = jwt_service.create_refresh_token(user_id, session_id)
        payload = jwt_service.verify_refresh_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["session_id"] == session_id
        assert payload["type"] == "refresh"

    def test_verify_refresh_token_expired(self, jwt_service: JwtService) -> None:
        """Test verifying an expired refresh token."""
        user_id = UserId(value=str(uuid.uuid4()))
        session_id = str(uuid.uuid4())

        # Create token in the past
        with freeze_time("2023-01-01"):
            token, _ = jwt_service.create_refresh_token(user_id, session_id)

        # Verify in the present (expired)
        with pytest.raises(JWTError):
            jwt_service.verify_refresh_token(token)

    def test_verify_refresh_token_invalid_signature(
        self, jwt_service: JwtService
    ) -> None:
        """Test verifying a refresh token with invalid signature."""
        payload = {
            "sub": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "type": "refresh",
            "exp": datetime.now(UTC) + timedelta(days=30),
            "iat": datetime.now(UTC),
        }
        invalid_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        with pytest.raises(JWTError):
            jwt_service.verify_refresh_token(invalid_token)

    def test_verify_refresh_token_wrong_type(self, jwt_service: JwtService) -> None:
        """Test verifying an access token as a refresh token."""
        user_id = UserId(value=str(uuid.uuid4()))
        email = "test@example.com"
        role = UserRole.viewer()
        access_token, _ = jwt_service.create_access_token(user_id, email, role)

        with pytest.raises(JWTError):
            jwt_service.verify_refresh_token(access_token)

    def test_extract_user_id(self, jwt_service: JwtService) -> None:
        """Test extracting user ID from token."""
        user_id = UserId(value=str(uuid.uuid4()))
        email = "test@example.com"
        role = UserRole.viewer()

        token, _ = jwt_service.create_access_token(user_id, email, role)
        extracted_user_id = jwt_service.extract_user_id(token)

        assert extracted_user_id == user_id

    def test_extract_user_id_invalid_token(self, jwt_service: JwtService) -> None:
        """Test extracting user ID from invalid token."""
        with pytest.raises(JWTError):
            jwt_service.extract_user_id("invalid_token")

    def test_extract_session_id(self, jwt_service: JwtService) -> None:
        """Test extracting session ID from refresh token."""
        user_id = UserId(value=str(uuid.uuid4()))
        session_id = str(uuid.uuid4())

        token, _ = jwt_service.create_refresh_token(user_id, session_id)
        extracted_session_id = jwt_service.extract_session_id(token)

        assert extracted_session_id == session_id

    def test_extract_session_id_from_access_token(self, jwt_service: JwtService) -> None:
        """Test extracting session ID from access token (should fail)."""
        user_id = UserId(value=str(uuid.uuid4()))
        email = "test@example.com"
        role = UserRole.viewer()

        token, _ = jwt_service.create_access_token(user_id, email, role)
        
        with pytest.raises(JWTError):
            jwt_service.extract_session_id(token)