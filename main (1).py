# =============================================================================
# main.py
# =============================================================================
# PURPOSE:
#   The application entry point. Responsibilities:
#     1. Create the FastAPI application instance
#     2. Register global exception handlers
#     3. Define all API routes and connect them to CRUD functions
#     4. Auto-create database tables on startup
#
# HOW ROUTES WORK:
#   HTTP Request → FastAPI Route → Pydantic Validates Input
#     → CRUD Function → SQLAlchemy → SQLite DB
#     → CRUD Returns ORM Object → Pydantic Serialises → JSON Response
#
# DEPENDENCY INJECTION:
#   `db: Session = Depends(get_db)` tells FastAPI:
#     "Before calling this route, run get_db(), and pass the result as `db`"
#   FastAPI handles this automatically — we never call get_db() ourselves.
# =============================================================================

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from typing import List

# Local imports
import models
import schemas
import crud
from database import engine, Base, get_db

# =============================================================================
# DATABASE TABLE AUTO-CREATION
# =============================================================================
# On startup, SQLAlchemy inspects all classes inheriting from Base (i.e. the
# User model in models.py) and runs CREATE TABLE IF NOT EXISTS for each one.
# This means the database schema always matches the ORM models automatically.
#
# NOTE: For production, use Alembic migrations instead. `create_all` doesn't
# handle schema changes (e.g., adding a new column to an existing table).
# =============================================================================
models.Base.metadata.create_all(bind=engine)

# =============================================================================
# FASTAPI APPLICATION INSTANCE
# =============================================================================
app = FastAPI(
    title="User Management API",
    description=(
        "A complete CRUD REST API for managing users.\n\n"
        "Built with **FastAPI**, **SQLAlchemy ORM**, and **SQLite**.\n\n"
        "Features: full CRUD, email uniqueness enforcement, input validation, "
        "proper HTTP status codes, and pagination."
    ),
    version="1.0.0",
    docs_url="/docs",      # Swagger UI available at http://localhost:8000/docs
    redoc_url="/redoc",    # ReDoc UI available at http://localhost:8000/redoc
)


# =============================================================================
# GLOBAL EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Override FastAPI's default 422 Validation Error response.

    Default FastAPI format is verbose and technical. We wrap it in a
    friendlier format consistent with our other error responses.

    Triggered automatically when a request body fails Pydantic validation
    (e.g., missing required field, invalid email format, age ≤ 0).
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation failed. Please check your input.",
            "errors": exc.errors()    # List of field-level error details
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for any unhandled Python exceptions.

    Prevents raw Python tracebacks from leaking to clients.
    In production, log `exc` to an error tracker (e.g., Sentry) here.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected internal server error occurred."
        }
    )


# =============================================================================
# HEALTH CHECK ROUTE
# =============================================================================

@app.get(
    "/",
    tags=["Health"],
    summary="Server health check"
)
def root():
    """
    Returns the server status.
    Useful for load balancers, uptime monitors, and quick sanity checks.
    """
    return {
        "status": "running",
        "message": "User Management API is online.",
        "version": "1.0.0",
        "docs": "/docs"
    }


# =============================================================================
# CREATE USER — POST /users
# =============================================================================

@app.post(
    "/users",
    response_model=schemas.UserCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
    summary="Create a new user",
    responses={
        201: {"description": "User created successfully"},
        409: {"description": "Email already exists"},
        422: {"description": "Validation error in request body"},
    }
)
def create_user(
    user_data: schemas.UserCreate,      # FastAPI parses & validates request body
    db: Session = Depends(get_db)       # FastAPI injects a DB session
):
    """
    Create a new user with name, email, and age.

    - **name**: Required, cannot be empty
    - **email**: Required, must be valid format, must be unique
    - **age**: Required, must be a positive integer

    Returns a success message. Use GET /users to retrieve the created user.
    """
    crud.create_user(db=db, user_data=user_data)
    return {"message": "User created successfully"}


# =============================================================================
# GET ALL USERS — GET /users
# =============================================================================

@app.get(
    "/users",
    response_model=List[schemas.UserResponse],
    status_code=status.HTTP_200_OK,
    tags=["Users"],
    summary="Retrieve all users",
)
def get_all_users(
    skip: int = 0,       # Pagination: skip this many records
    limit: int = 100,    # Pagination: return at most this many
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of all users.

    Supports pagination:
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Max records to return (default: 100)

    Example: `GET /users?skip=0&limit=10` returns the first 10 users.
    """
    users = crud.get_users(db=db, skip=skip, limit=limit)
    return users


# =============================================================================
# GET USER BY ID — GET /users/{id}
# =============================================================================

@app.get(
    "/users/{user_id}",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_200_OK,
    tags=["Users"],
    summary="Get a user by ID",
    responses={
        200: {"description": "User found and returned"},
        404: {"description": "User not found"},
    }
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve a single user by their unique ID.

    Returns 404 if no user exists with the given ID.
    """
    user = crud.get_user(db=db, user_id=user_id)
    return user


# =============================================================================
# UPDATE USER — PUT /users/{id}
# =============================================================================

@app.put(
    "/users/{user_id}",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_200_OK,
    tags=["Users"],
    summary="Update a user",
    responses={
        200: {"description": "User updated successfully"},
        400: {"description": "No update fields provided"},
        404: {"description": "User not found"},
        409: {"description": "Updated email already taken"},
        422: {"description": "Validation error"},
    }
)
def update_user(
    user_id: int,
    update_data: schemas.UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update one or more fields of an existing user.

    All fields are optional — send only the fields you want to change:

    - `{ "age": 30 }` → updates only age
    - `{ "name": "Jane", "email": "jane@example.com" }` → updates name and email
    - `{}` → returns 400 (nothing to update)
    """
    updated_user = crud.update_user(db=db, user_id=user_id, update_data=update_data)
    return updated_user


# =============================================================================
# DELETE USER — DELETE /users/{id}
# =============================================================================

@app.delete(
    "/users/{user_id}",
    response_model=schemas.MessageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Users"],
    summary="Delete a user",
    responses={
        200: {"description": "User deleted successfully"},
        404: {"description": "User not found"},
    }
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Permanently delete a user by ID.

    This action is irreversible. Returns 404 if the user does not exist.
    """
    result = crud.delete_user(db=db, user_id=user_id)
    return result
