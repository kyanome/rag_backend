"""JWT token service for authentication."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from ...domain.value_objects import UserId, UserRole
from ...infrastructure.config.settings import Settings


class JwtService:
    """JWT token generation and validation service."""

    def __init__(self, settings: Settings) -> None:
        """Initialize JWT service with settings."""
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = settings.refresh_token_expire_days

    def create_access_token(
        self, user_id: UserId, email: str, role: UserRole
    ) -> tuple[str, datetime]:
        """Create an access token for a user.

        Args:
            user_id: User's ID
            email: User's email address
            role: User's role

        Returns:
            Tuple of (token, expiration_datetime)
        """
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role.name.value,
            "type": "access",
            "exp": expire,
            "iat": now,
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expire

    def create_refresh_token(
        self, user_id: UserId, session_id: str
    ) -> tuple[str, datetime]:
        """Create a refresh token for a user session.

        Args:
            user_id: User's ID
            session_id: Session ID to associate with the refresh token

        Returns:
            Tuple of (token, expiration_datetime)
        """
        now = datetime.now(UTC)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": str(user_id),
            "session_id": session_id,
            "type": "refresh",
            "exp": expire,
            "iat": now,
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expire

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT token.

        Args:
            token: JWT token to decode

        Returns:
            Decoded token payload

        Raises:
            JWTError: If token is invalid, expired, or cannot be decoded
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            raise JWTError(f"Invalid token: {str(e)}") from e

    def verify_access_token(self, token: str) -> dict[str, Any]:
        """Verify an access token and return its payload.

        Args:
            token: Access token to verify

        Returns:
            Token payload if valid

        Raises:
            JWTError: If token is invalid or not an access token
        """
        payload = self.decode_token(token)

        if payload.get("type") != "access":
            raise JWTError("Token is not an access token")

        return payload

    def verify_refresh_token(self, token: str) -> dict[str, Any]:
        """Verify a refresh token and return its payload.

        Args:
            token: Refresh token to verify

        Returns:
            Token payload if valid

        Raises:
            JWTError: If token is invalid or not a refresh token
        """
        payload = self.decode_token(token)

        if payload.get("type") != "refresh":
            raise JWTError("Token is not a refresh token")

        return payload

    def extract_user_id(self, token: str) -> UserId:
        """Extract user ID from a token.

        Args:
            token: JWT token

        Returns:
            User ID

        Raises:
            JWTError: If token is invalid or user ID is missing
        """
        payload = self.decode_token(token)
        user_id_str = payload.get("sub")

        if not user_id_str:
            raise JWTError("User ID not found in token")

        try:
            return UserId(user_id_str)
        except ValueError as e:
            raise JWTError(f"Invalid user ID in token: {str(e)}") from e

    def extract_session_id(self, refresh_token: str) -> str:
        """Extract session ID from a refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            Session ID

        Raises:
            JWTError: If token is invalid or session ID is missing
        """
        payload = self.verify_refresh_token(refresh_token)
        session_id = payload.get("session_id")

        if not session_id:
            raise JWTError("Session ID not found in refresh token")

        return session_id  # type: ignore[no-any-return]
