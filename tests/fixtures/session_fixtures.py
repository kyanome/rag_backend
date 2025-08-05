"""Helper functions for creating test sessions with expired timestamps."""

from datetime import UTC, datetime, timedelta

from src.domain.entities import Session as DomainSession
from src.domain.value_objects import UserId


def create_expired_session(
    user_id: UserId,
    hours_ago: int = 24,
    session_suffix: str = "",
) -> DomainSession:
    """Create an expired session for testing.
    
    This bypasses the validation in __post_init__ by creating the session
    in a controlled way.
    """
    import uuid
    session_id = f"expired_{uuid.uuid4()}{session_suffix}"
    now = datetime.now(UTC)
    expired_time = now - timedelta(hours=hours_ago)
    
    # Create session dict without triggering validation
    session_data = {
        "id": session_id,
        "user_id": user_id,
        "access_token": f"expired_access_{session_id}",
        "refresh_token": f"expired_refresh_{session_id}",
        "access_token_expires_at": expired_time,
        "refresh_token_expires_at": expired_time,
        "created_at": expired_time - timedelta(days=1),
        "last_accessed_at": expired_time,
        "ip_address": "192.168.1.1",
        "user_agent": "Test Agent",
    }
    
    # Create the session object directly
    session = DomainSession.__new__(DomainSession)
    for key, value in session_data.items():
        setattr(session, key, value)
    
    return session