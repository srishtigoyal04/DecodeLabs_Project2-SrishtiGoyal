# =============================================================================
# crud.py
# =============================================================================
# PURPOSE:
#   Contains all database operations (Create, Read, Update, Delete).
#   This is the "data access layer" — the only place that talks to the DB.
#
# WHY A SEPARATE CRUD LAYER?
#   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
#   │  Client  │───▶│  Route   │───▶│   CRUD   │───▶│    DB    │
#   │(Postman) │    │(main.py) │    │(crud.py) │    │(SQLite)  │
#   └──────────┘    └──────────┘    └──────────┘    └──────────┘
#
#   - Routes handle HTTP concerns (status codes, request parsing, responses)
#   - CRUD functions handle database concerns (queries, commits, rollbacks)
#   - This separation makes the code testable and maintainable.
#   - You can test CRUD functions without starting an HTTP server.
#
# HOW SQLALCHEMY ORM WORKS (vs raw SQL):
#   Raw SQL:  cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
#   ORM:      db.query(User).filter(User.id == user_id).first()
#   Both do the same thing. ORM is safer (no SQL injection) and more Pythonic.
# =============================================================================

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

import models
import schemas


# =============================================================================
# CREATE USER
# =============================================================================
def create_user(db: Session, user_data: schemas.UserCreate) -> models.User:
    """
    Insert a new user record into the database.

    DUPLICATE EMAIL PREVENTION:
    ─────────────────────────────────────────────────────────────────────────
    We use a TWO-LAYER approach to prevent duplicate emails:

    Layer 1 — Application Check (before insert):
        We query the DB first to see if the email already exists.
        If it does, we raise a 409 Conflict HTTP error immediately.
        This gives us a clear, meaningful error message.

    Layer 2 — Database Constraint (safety net):
        The `users` table has `unique=True` on the email column.
        Even if Layer 1 somehow fails (race condition, bug), the DB itself
        will reject the duplicate with an IntegrityError.
        We catch that too and convert it into a proper 409 response.

    WHY BOTH LAYERS?
        Layer 1 alone: Race condition possible (two requests at same time).
        Layer 2 alone: IntegrityError message is ugly, hard to format nicely.
        Together: Clean UX + bulletproof data integrity.
    ─────────────────────────────────────────────────────────────────────────

    Args:
        db:        Active database session (injected by FastAPI)
        user_data: Validated user data from the request body

    Returns:
        The newly created User ORM object (with id populated)

    Raises:
        HTTPException 409: If email already exists
    """

    # ── Layer 1: Application-level duplicate check ──────────────────────────
    existing_user = db.query(models.User).filter(
        models.User.email == user_data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{user_data.email}' already exists."
        )

    # ── Create ORM object from validated Pydantic data ──────────────────────
    # `model_dump()` converts Pydantic model → Python dict
    # `**` unpacks the dict as keyword arguments to the User constructor
    new_user = models.User(**user_data.model_dump())

    try:
        db.add(new_user)      # Stage the INSERT (not sent to DB yet)
        db.commit()           # Send INSERT to DB and save permanently
        db.refresh(new_user)  # Reload from DB to get the auto-assigned `id`
        return new_user

    except IntegrityError:
        # ── Layer 2: DB-level constraint catches race conditions ─────────────
        db.rollback()         # Undo any pending changes to keep DB clean
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{user_data.email}' already exists."
        )


# =============================================================================
# GET ALL USERS
# =============================================================================
def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[models.User]:
    """
    Retrieve all users from the database with optional pagination.

    HOW THE ORM QUERY WORKS:
        db.query(User)       → SELECT * FROM users
        .offset(skip)        → OFFSET 0  (skip N records for pagination)
        .limit(limit)        → LIMIT 100 (return at most 100 records)
        .all()               → execute and return a Python list

    PAGINATION:
        Use `skip` and `limit` for efficient data loading.
        GET /users?skip=0&limit=10  → first 10 users
        GET /users?skip=10&limit=10 → next 10 users (page 2)

    Args:
        db:    Active database session
        skip:  Number of records to skip (offset)
        limit: Maximum number of records to return

    Returns:
        List of User ORM objects
    """
    return db.query(models.User).offset(skip).limit(limit).all()


# =============================================================================
# GET USER BY ID
# =============================================================================
def get_user(db: Session, user_id: int) -> models.User:
    """
    Retrieve a single user by their primary key (id).

    HOW THE ORM QUERY WORKS:
        db.query(User)              → SELECT * FROM users
        .filter(User.id == user_id) → WHERE id = <user_id>
        .first()                    → LIMIT 1, return first result or None

    `.first()` returns `None` if no row matches (never raises an exception).
    We then manually raise a 404 if nothing was found.

    Args:
        db:      Active database session
        user_id: The integer primary key to look up

    Returns:
        User ORM object

    Raises:
        HTTPException 404: If no user exists with that id
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found."
        )

    return user


# =============================================================================
# UPDATE USER
# =============================================================================
def update_user(
    db: Session,
    user_id: int,
    update_data: schemas.UserUpdate
) -> models.User:
    """
    Update an existing user's fields (partial update supported).

    HOW PARTIAL UPDATE WORKS:
        `model_dump(exclude_unset=True)` returns ONLY the fields the client
        actually sent in the request body. Fields not included in the JSON
        are excluded from the update dict.

        Example:
            Client sends: { "age": 30 }
            `exclude_unset=True` returns: {"age": 30}
            Only age gets updated; name and email stay unchanged.

        WITHOUT `exclude_unset=True`:
            Returns: {"name": None, "email": None, "age": 30}
            This would overwrite name and email with NULL — data loss!

    DUPLICATE EMAIL CHECK ON UPDATE:
        If the client is changing the email, we check that the new email
        isn't already taken by a DIFFERENT user (excluding current user's id).

    Args:
        db:          Active database session
        user_id:     ID of the user to update
        update_data: Pydantic model with optional update fields

    Returns:
        Updated User ORM object

    Raises:
        HTTPException 404: If user not found
        HTTPException 409: If updated email already belongs to another user
    """

    # Step 1: Find the user (raises 404 if not found)
    user = get_user(db, user_id)

    # Step 2: Extract only the fields the client explicitly sent
    update_fields = update_data.model_dump(exclude_unset=True)

    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided. Send at least one field to update."
        )

    # Step 3: If email is being changed, check for conflicts with OTHER users
    if "email" in update_fields:
        conflict = db.query(models.User).filter(
            models.User.email == update_fields["email"],
            models.User.id != user_id          # Exclude the current user
        ).first()

        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{update_fields['email']}' is already taken by another user."
            )

    # Step 4: Apply each updated field to the ORM object
    # `setattr(obj, key, value)` is equivalent to `obj.key = value`
    # but works dynamically when the key is a variable string.
    for field, value in update_fields.items():
        setattr(user, field, value)

    # Step 5: Commit changes to the database
    try:
        db.commit()
        db.refresh(user)   # Reload to confirm what was saved
        return user

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists (database constraint)."
        )


# =============================================================================
# DELETE USER
# =============================================================================
def delete_user(db: Session, user_id: int) -> dict:
    """
    Permanently delete a user from the database.

    HOW IT WORKS:
        1. Find the user (raises 404 if not found)
        2. Call `db.delete(user)` to stage a DELETE statement
        3. Call `db.commit()` to execute and make it permanent

    Args:
        db:      Active database session
        user_id: ID of the user to delete

    Returns:
        dict with success message

    Raises:
        HTTPException 404: If user not found
    """

    # Find the user (get_user raises 404 automatically if not found)
    user = get_user(db, user_id)

    db.delete(user)    # Stage DELETE FROM users WHERE id = <user_id>
    db.commit()        # Execute permanently

    return {"message": f"User with id={user_id} deleted successfully."}
