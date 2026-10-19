# Initial LLD — Users Service

**Document ID:** LLD-USERS-001  
**Status:** DRAFT  
**Service:** users  
**Linked:** [`HLD`](hld.md), [`SRS`](srs.md), [`API-CONTRACTS`](api-contracts.md), [`PLAN.md`](../PLAN.md)

**Ponytail note:** This is the first service to be implemented per PLAN.md task list. Design is minimal — stdlib-first, no unrequested abstractions.

## 1. Responsibilities
- User registration (email + password)
- User login (validate credentials, issue JWT)
- Get user profile (authenticated)
- Publish `user.created`, `user.updated` events

## 2. Database schema (SQLite dev / PostgreSQL prod)

Table: `users`

| Column | Type | Constraint |
|---|---|---|
| id | UUID / INTEGER | PRIMARY KEY |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| password_hash | VARCHAR(255) | NOT NULL |
| created_at | TIMESTAMP | NOT NULL, default now() |
| updated_at | TIMESTAMP | NOT NULL, default now() |

Table: `outbox` (transactional outbox)

| Column | Type | Constraint |
|---|---|---|
| id | UUID / INTEGER | PRIMARY KEY |
| aggregate_type | VARCHAR(50) | NOT NULL (e.g., "user") |
| aggregate_id | VARCHAR(255) | NOT NULL |
| event_type | VARCHAR(50) | NOT NULL (e.g., "user.created") |
| payload | JSON | NOT NULL |
| created_at | TIMESTAMP | NOT NULL, default now() |
| published_at | TIMESTAMP | NULLABLE |

## 3. HTTP API

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | /users/register | Register new user | None |
| POST | /users/login | Authenticate, issue JWT | None |
| GET | /users/profile | Get current user profile | JWT required |

## 4. Event publishing

| Event | Stream | Trigger |
|---|---|---|
| user.created | user-events | After user insert committed |
| user.updated | user-events | After user update committed |

Published via transactional outbox: event row inserted in same DB transaction as user row; outbox relay publishes to Redis Streams.

## 5. JWT handling
- Issued by users service on login/registration
- Validated by gateway (identity centralization)
- Each service re-validates for authorization (defense in depth)
- Secret: `JWT_SECRET_KEY` environment variable (never committed), 32+ bytes
- Access token TTL: 60 minutes (`DECIDED`)

## 6. Dependencies
- `fastapi`, `sqlalchemy`, `alembic`, `PyJWT`
- `redis` (for outbox relay / shared helpers)

## 7. Open questions
- Password hashing algorithm: stdlib `pbkdf2_hmac` (`RECOMMENDATION`)
- JWT refresh token rotation? (`OPEN` — out of MVP scope)
