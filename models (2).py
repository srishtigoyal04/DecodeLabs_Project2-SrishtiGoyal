# =============================================================================
# models.py
# =============================================================================
# PURPOSE:
#   Defines the SQLAlchemy ORM model for the `users` database table.
#   An ORM model is a Python class where each attribute represents a column.
#
# HOW ORM WORKS:
#   ORM = Object-Relational Mapper.
#   Instead of writing raw SQL like:
#       INSERT INTO users (name, email, age) VALUES ('John', 'j@x.com', 25)
#   You write Python like:
#       user = User(name="John", email="j@x.com", age=25)
#       db.add(user)
#       db.commit()
#   SQLAlchemy converts your Python code into SQL automatically.
#
# WHY SEPARATE FROM schemas.py?
#   - models.py   → Talks to the DATABASE (SQLAlchemy)
#   - schemas.py  → Talks to the CLIENT via HTTP (Pydantic)
#   They serve different purposes and should stay separate.
# =============================================================================

from sqlalchemy import Column, Integer, String
from database import Base


class User(Base):
    """
    SQLAlchemy ORM model representing the `users` table in the database.

    Every class attribute with `Column(...)` becomes a column in the table.
    SQLAlchemy uses this class definition to generate and validate the schema.
    """

    # -------------------------------------------------------------------------
    # TABLE NAME
    # -------------------------------------------------------------------------
    # Tells SQLAlchemy what to name the table in the database.
    # Convention: lowercase, plural form of the model class name.
    # -------------------------------------------------------------------------
    __tablename__ = "users"

    # -------------------------------------------------------------------------
    # COLUMNS
    # -------------------------------------------------------------------------

    # PRIMARY KEY
    # `Integer`      → stored as a number
    # `primary_key`  → uniquely identifies each row
    # `index=True`   → creates a B-tree index for fast lookups by id
    # Auto-increment is automatic for Integer primary keys in SQLite.
    id = Column(Integer, primary_key=True, index=True)

    # NAME
    # `String(100)` → VARCHAR(100) in SQL, max 100 characters
    # `nullable=False` → this column is REQUIRED (cannot be NULL)
    name = Column(String(100), nullable=False)

    # EMAIL
    # `unique=True`  → database-level constraint; duplicate emails are rejected
    # `index=True`   → speeds up queries that search/filter by email
    # Both `unique` and `nullable=False` enforce data integrity at the DB level,
    # even if the application layer somehow misses the validation.
    email = Column(String(255), nullable=False, unique=True, index=True)

    # AGE
    # Simple integer column, required (not null)
    age = Column(Integer, nullable=False)

    # -------------------------------------------------------------------------
    # __repr__ (optional but helpful for debugging)
    # -------------------------------------------------------------------------
    # When you `print(user)` in the terminal, this shows something useful
    # instead of <User object at 0x7f...>
    # -------------------------------------------------------------------------
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}', age={self.age})>"
