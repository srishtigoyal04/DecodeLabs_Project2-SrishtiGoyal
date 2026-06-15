# User Management API

A complete CRUD REST API built with **FastAPI**, **SQLAlchemy ORM**, and **SQLite**.

---

## Project Structure

```
user-management-api/
├── main.py                 # FastAPI app + all route definitions
├── database.py             # DB engine, session factory, Base class, get_db dependency
├── models.py               # SQLAlchemy ORM model (User → users table)
├── schemas.py              # Pydantic schemas for request validation & response shaping
├── crud.py                 # All database operations (Create, Read, Update, Delete)
├── requirements.txt        # Pinned Python dependencies
├── postman_collection.json # 13 ready-to-import Postman test requests
└── README.md               # This file
```

---

## What Each File Does

| File | Layer | Responsibility |
|---|---|---|
| `database.py` | Infrastructure | DB connection, session factory, dependency injection |
| `models.py` | Data | Defines the `users` table via SQLAlchemy ORM |
| `schemas.py` | API Contract | Validates incoming requests; shapes outgoing responses |
| `crud.py` | Business Logic | All DB read/write operations |
| `main.py` | HTTP | Route definitions, exception handlers, app startup |

---

## Setup & Run

### 1. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the server

```bash
uvicorn main:app --reload
```

`--reload` auto-restarts on file changes (development only).

The API is now running at **http://127.0.0.1:8000**

### 4. Explore the interactive docs

| UI | URL |
|---|---|
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |

---

## API Endpoints

### Base URL: `http://127.0.0.1:8000`

| Method | Path | Description | Success Code |
|---|---|---|---|
| GET | `/` | Health check | 200 |
| POST | `/users` | Create a user | 201 |
| GET | `/users` | Get all users | 200 |
| GET | `/users/{id}` | Get user by ID | 200 |
| PUT | `/users/{id}` | Update a user | 200 |
| DELETE | `/users/{id}` | Delete a user | 200 |

---

## Example Requests & Responses

### POST /users — Create User

**Request:**
```json
POST /users
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "age": 25
}
```

**Response 201 — Created:**
```json
{
  "message": "User created successfully"
}
```

**Response 409 — Duplicate Email:**
```json
{
  "detail": "A user with email 'john@example.com' already exists."
}
```

**Response 422 — Validation Error:**
```json
{
  "success": false,
  "message": "Validation failed. Please check your input.",
  "errors": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    },
    {
      "loc": ["body", "age"],
      "msg": "Input should be greater than 0",
      "type": "greater_than"
    }
  ]
}
```

---

### GET /users — List All Users

**Request:**
```
GET /users?skip=0&limit=10
```

**Response 200:**
```json
[
  { "id": 1, "name": "John Doe",   "email": "john@example.com", "age": 25 },
  { "id": 2, "name": "Jane Smith", "email": "jane@example.com", "age": 30 }
]
```

---

### GET /users/{id} — Get by ID

**Response 200:**
```json
{ "id": 1, "name": "John Doe", "email": "john@example.com", "age": 25 }
```

**Response 404:**
```json
{ "detail": "User with id=999 not found." }
```

---

### PUT /users/{id} — Update User (partial updates supported)

**Request (update age only):**
```json
{ "age": 26 }
```

**Response 200:**
```json
{ "id": 1, "name": "John Doe", "email": "john@example.com", "age": 26 }
```

---

### DELETE /users/{id} — Delete User

**Response 200:**
```json
{ "message": "User with id=1 deleted successfully." }
```

---

## How CRUD Works

```
C — Create  →  POST   /users           → INSERT INTO users ...
R — Read    →  GET    /users           → SELECT * FROM users
             →  GET    /users/{id}      → SELECT * FROM users WHERE id=N
U — Update  →  PUT    /users/{id}      → UPDATE users SET ... WHERE id=N
D — Delete  →  DELETE /users/{id}      → DELETE FROM users WHERE id=N
```

Each letter in CRUD maps to a standard HTTP method and a SQL statement.
The application never writes raw SQL — SQLAlchemy generates it from Python.

---

## How ORM Works

ORM = **Object-Relational Mapper**

It translates between Python objects and database rows:

| Without ORM (raw SQL) | With ORM (SQLAlchemy) |
|---|---|
| `cursor.execute("INSERT INTO users ...")` | `db.add(User(name=..., email=..., age=...))` |
| `cursor.execute("SELECT * FROM users WHERE id=?", (1,))` | `db.query(User).filter(User.id == 1).first()` |
| `cursor.execute("UPDATE users SET age=? WHERE id=?", (30, 1))` | `user.age = 30; db.commit()` |
| `cursor.execute("DELETE FROM users WHERE id=?", (1,))` | `db.delete(user); db.commit()` |

**Benefits of ORM:**
- No SQL injection risk (parameterisation is automatic)
- Work with Python objects instead of raw rows/dicts
- Database-agnostic (swap SQLite → PostgreSQL by changing one line)
- Schema defined once in Python, not separately in SQL

---

## How Duplicate Email Prevention Works

Two independent layers protect against duplicate emails:

```
Client Request
      │
      ▼
┌─────────────────────────────────────────────┐
│  Layer 1: Application Check (crud.py)       │
│  SELECT * FROM users WHERE email = 'x'      │
│  If found → raise HTTPException 409         │
└─────────────────────────────────────────────┘
      │ (passes)
      ▼
┌─────────────────────────────────────────────┐
│  Layer 2: Database Constraint (models.py)   │
│  email = Column(..., unique=True)           │
│  DB rejects duplicate → IntegrityError      │
│  We catch it → raise HTTPException 409      │
└─────────────────────────────────────────────┘
      │ (passes)
      ▼
   User Created ✓
```

Layer 1 handles the normal case cleanly.
Layer 2 is a safety net for race conditions (two requests arriving simultaneously).

---

## HTTP Status Codes Used

| Code | Meaning | When Used |
|---|---|---|
| 200 OK | Success | GET, PUT, DELETE success |
| 201 Created | Resource created | POST /users success |
| 400 Bad Request | Client error | No update fields provided |
| 404 Not Found | Resource missing | User ID doesn't exist |
| 409 Conflict | Duplicate | Email already in use |
| 422 Unprocessable | Validation failed | Invalid email, negative age, empty name |
| 500 Internal Error | Server bug | Unhandled exception |

---

## Postman Testing

Import `postman_collection.json`:
1. Open Postman → **Import** → **Upload Files**
2. Select `postman_collection.json`
3. The collection `User Management API` appears with 13 pre-built requests
4. The `{{base_url}}` variable is pre-set to `http://127.0.0.1:8000`

Run requests in order (1→13) to test the full CRUD lifecycle.

---

## Common Interview Questions

**Q: What is the difference between ORM and raw SQL?**
A: ORM lets you interact with the database using Python objects and methods. Raw SQL requires you to write SQL strings manually. ORM prevents SQL injection automatically and is database-agnostic.

**Q: What is dependency injection in FastAPI?**
A: `Depends(get_db)` tells FastAPI to call `get_db()` before the route handler and pass the result as a parameter. This ensures each request gets a fresh DB session that is always closed afterward.

**Q: Why use `exclude_unset=True` in the update endpoint?**
A: It returns only the fields the client explicitly sent. Without it, optional fields default to `None` and would overwrite existing data with NULL values.

**Q: What is the difference between `db.flush()` and `db.commit()`?**
A: `flush()` sends pending SQL to the DB within the current transaction (visible only to this session). `commit()` permanently saves all changes and makes them visible to all connections.

**Q: How does SQLAlchemy prevent SQL injection?**
A: It uses parameterised queries internally. User input is never directly concatenated into SQL strings — values are passed as separate parameters that the DB driver escapes safely.

**Q: What is a 409 status code?**
A: HTTP 409 Conflict indicates the request could not be completed because it conflicts with the current state of the server — typically used for duplicate unique-constraint violations.

**Q: Why separate schemas.py and models.py?**
A: Models define the database schema (SQLAlchemy). Schemas define the API contract (Pydantic). They serve different purposes. Mixing them creates tight coupling, makes testing harder, and risks exposing internal DB columns (like password hashes) in API responses.
