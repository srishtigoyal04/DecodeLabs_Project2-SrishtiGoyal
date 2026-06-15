# =============================================================================
# database.py
# =============================================================================
# PURPOSE:
#   This file is the foundation of the entire database layer.
#   It creates and configures:
#     1. The SQLAlchemy Engine  → the actual connection to SQLite
#     2. The SessionLocal       → a factory that creates DB sessions per request
#     3. The Base class         → parent class all ORM models inherit from
#
# WHY SEPARATE?
#   Keeping DB config in one place means if you ever switch from SQLite to
#   PostgreSQL, you only change this file. Nothing else needs to change.
# =============================================================================

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# -----------------------------------------------------------------------------
# DATABASE URL
# -----------------------------------------------------------------------------
# SQLite stores everything in a single file: `users.db`
# The `sqlite:///` prefix tells SQLAlchemy to use SQLite.
# Three slashes = relative path (file created in current directory).
# Four slashes  = absolute path (e.g., sqlite:////home/user/app/users.db)
# -----------------------------------------------------------------------------
DATABASE_URL = "sqlite:///./users.db"

# -----------------------------------------------------------------------------
# ENGINE
# -----------------------------------------------------------------------------
# The engine is the core interface between Python and the database.
# It manages the connection pool and translates Python ORM calls into SQL.
#
# `check_same_thread=False` is a SQLite-specific argument:
#   - By default, SQLite only allows access from the thread that created it.
#   - FastAPI uses multiple threads, so we must disable this restriction.
#   - This is safe here because SQLAlchemy manages thread safety for us.
# -----------------------------------------------------------------------------
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# -----------------------------------------------------------------------------
# SESSION FACTORY
# -----------------------------------------------------------------------------
# `SessionLocal` is a class (factory) that creates new database session
# objects. Each HTTP request gets its own session, which is like a "unit of
# work" — it tracks all changes and sends them to the DB together.
#
# `autocommit=False` → We control when to commit (save) changes manually.
#                      This allows us to roll back on errors.
# `autoflush=False`  → SQLAlchemy won't auto-send pending SQL before queries.
#                      We control exactly when SQL is executed.
# `bind=engine`      → Links this session factory to our SQLite engine.
# -----------------------------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# -----------------------------------------------------------------------------
# DECLARATIVE BASE
# -----------------------------------------------------------------------------
# `Base` is the parent class that all ORM models (tables) must inherit from.
# When you call `Base.metadata.create_all(engine)`, SQLAlchemy looks at every
# class that inherits from Base, reads their column definitions, and creates
# the corresponding tables in the database.
# -----------------------------------------------------------------------------
Base = declarative_base()


# -----------------------------------------------------------------------------
# DATABASE DEPENDENCY (Dependency Injection)
# -----------------------------------------------------------------------------
# This generator function is used with FastAPI's `Depends()` system.
# FastAPI calls this function before each request and injects the `db`
# session into the route handler automatically.
#
# HOW IT WORKS:
#   1. `db = SessionLocal()` creates a new session for this request.
#   2. `yield db` pauses the function and gives the session to the route.
#   3. The route handler does its database work.
#   4. After the route finishes (success or error), execution resumes here.
#   5. `finally: db.close()` ALWAYS runs, ensuring no connection leaks.
#
# This pattern is called a "context manager" and guarantees cleanup.
# -----------------------------------------------------------------------------
def get_db():
    """
    Dependency that provides a database session per request.
    Always closes the session when the request is done.
    """
    db = SessionLocal()
    try:
        yield db          # Hand session to the route handler
    finally:
        db.close()        # Always close, even if an exception was raised
