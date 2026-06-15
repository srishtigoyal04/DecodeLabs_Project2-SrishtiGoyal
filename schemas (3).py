# =============================================================================
# schemas.py
# =============================================================================
# PURPOSE:
#   Defines Pydantic models (schemas) used for:
#     1. REQUEST VALIDATION  → Validate and parse incoming JSON from clients
#     2. RESPONSE SHAPING    → Define what JSON structure we send back
#
# PYDANTIC vs SQLALCHEMY MODELS:
#   ┌─────────────────┬──────────────────────────────────────────────────┐
#   │ SQLAlchemy Model│ Represents a DATABASE TABLE (models.py)          │
#   │                 │ Used to read/write rows from the DB              │
#   ├─────────────────┼──────────────────────────────────────────────────┤
#   │ Pydantic Schema │ Represents an API CONTRACT (schemas.py)          │
#   │                 │ Used to validate HTTP request bodies & responses │
#   └─────────────────┴──────────────────────────────────────────────────┘
#
# WHY BOTH?
#   - The DB may have internal columns (created_at, password_hash) we never
#     expose to clients. Schemas control exactly what goes in and comes out.
#   - Pydantic provides automatic type coercion and rich validation errors.
# =============================================================================

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional


# =============================================================================
# UserCreate — Schema for POST /users (creating a new user)
# =============================================================================
class UserCreate(BaseModel):
    """
    Validates the request body when a client creates a new user.
    FastAPI automatically rejects requests that don't match this shape.
    """

    name: str = Field(
        ...,                        # `...` means this field is REQUIRED
        min_length=1,               # Cannot be empty string
        max_length=100,
        description="Full name of the user",
        examples=["John Doe"]
    )

    email: EmailStr = Field(
        ...,
        description="Valid, unique email address",
        examples=["john@example.com"]
    )

    age: int = Field(
        ...,
        gt=0,                       # `gt=0` means age must be Greater Than 0
        lt=150,                     # Reasonable upper bound
        description="Age must be a positive integer",
        examples=[25]
    )

    # -------------------------------------------------------------------------
    # CUSTOM VALIDATOR
    # -------------------------------------------------------------------------
    # `@field_validator` runs AFTER Pydantic's built-in type checking.
    # Here we strip accidental whitespace from the name field.
    # If name becomes empty after stripping, we raise a ValueError.
    # -------------------------------------------------------------------------
    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        """Strip whitespace and ensure the name is not empty."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name cannot be blank or whitespace only.")
        return stripped


# =============================================================================
# UserUpdate — Schema for PUT /users/{id} (updating an existing user)
# =============================================================================
class UserUpdate(BaseModel):
    """
    All fields are Optional so clients can send partial updates.
    Only provided fields will be updated; omitted fields stay unchanged.

    Example — update only the age:
        PUT /users/1
        Body: { "age": 30 }
        → Only age changes, name and email stay the same.
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated name (leave out to keep current)",
    )

    email: Optional[EmailStr] = Field(
        default=None,
        description="Updated email address (must still be unique)",
    )

    age: Optional[int] = Field(
        default=None,
        gt=0,
        lt=150,
        description="Updated age (must be positive)",
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: Optional[str]) -> Optional[str]:
        """If name is provided, ensure it's not just whitespace."""
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Name cannot be blank or whitespace only.")
            return stripped
        return value


# =============================================================================
# UserResponse — Schema for all responses that return user data
# =============================================================================
class UserResponse(BaseModel):
    """
    Defines what a user object looks like when returned to the client.
    Includes `id` (auto-generated by the DB) plus all user fields.

    `model_config = {"from_attributes": True}` tells Pydantic to read data
    from SQLAlchemy ORM objects (which have attributes, not dict keys).
    Without this, Pydantic would fail when given an ORM object.
    """

    id: int = Field(..., description="Auto-assigned unique identifier")
    name: str
    email: str
    age: int

    # Pydantic v2 config — allows reading from ORM model attributes
    model_config = {"from_attributes": True}


# =============================================================================
# Standard response envelopes
# =============================================================================

class MessageResponse(BaseModel):
    """Simple response for operations that don't return user data (e.g. delete)."""
    message: str


class UserCreatedResponse(BaseModel):
    """Response returned after successfully creating a user."""
    message: str
