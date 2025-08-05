"""Register user use case implementation."""

from dataclasses import dataclass

from ....domain.entities import User
from ....domain.exceptions.auth_exceptions import UserAlreadyExistsException
from ....domain.repositories import UserRepository
from ....domain.value_objects import Email, HashedPassword, UserRole


@dataclass
class RegisterUserInput:
    """Register user use case input."""

    email: str
    password: str
    name: str
    role: str = "viewer"


@dataclass
class RegisterUserOutput:
    """Register user use case output."""

    user: User
    success: bool


class RegisterUserUseCase:
    """Use case for user registration."""

    def __init__(self, user_repository: UserRepository) -> None:
        """Initialize register user use case."""
        self.user_repository = user_repository

    async def execute(self, input_data: RegisterUserInput) -> RegisterUserOutput:
        """Execute register user use case.

        Args:
            input_data: Registration input data

        Returns:
            Registration output with created user

        Raises:
            UserAlreadyExistsError: If user with email already exists
            ValueError: If input data is invalid
        """
        # Validate and create value objects
        try:
            email = Email(input_data.email)
            hashed_password = HashedPassword.from_plain_password(input_data.password)
            role = UserRole.from_name(input_data.role)
        except ValueError as e:
            raise ValueError(f"Invalid input data: {str(e)}") from e

        # Check if user already exists
        existing_user = await self.user_repository.find_by_email(email)
        if existing_user:
            raise UserAlreadyExistsException(f"User with email {email.value} already exists")

        # Create new user
        user = User.create(
            email=email,
            hashed_password=hashed_password,
            name=input_data.name,
            role=role,
        )

        # Save user
        await self.user_repository.save(user)

        return RegisterUserOutput(
            user=user,
            success=True,
        )

