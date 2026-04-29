# Building a Payment-Integrated Event Ticketing Platform
### FastAPI + PostgreSQL + Paystack — A Learning Guide

> **Philosophy:** We build this together, section by section. Every line of code is explained. Every Paystack concept is unpacked. By the end, you won't just have working payment integration — you'll understand *why* it works.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Conceptual Customer Journey](#2-conceptual-customer-journey)
3. [Platform Features & Scope](#3-platform-features--scope)
4. [Backend Architecture](#4-backend-architecture)
5. [API Endpoints Map](#5-api-endpoints-map)
6. [Database Design](#6-database-design)
7. [Paystack Ecosystem Concepts](#7-paystack-ecosystem-concepts)
8. [Data Balancing: Your DB vs Paystack](#8-data-balancing-your-db-vs-paystack)
9. [Key Backend Topics We Will Cover](#9-key-backend-topics-we-will-cover)
10. [Build Sequence (Section by Section)](#10-build-sequence-section-by-section)
11. [Environment & Tools Setup](#11-environment--tools-setup)
12. [Why FastAPI for This Project](#12-why-fastapi-for-this-project)

---

## 1. Project Overview

**Platform Name:** `TicketFlow` *(working name)*

**What it is:** A backend system for an event ticketing platform where organizers create events, customers purchase tickets, and payments are processed via Paystack.

**What it is NOT:** We will not build a frontend UI. Our "frontend" is a REST API that any client (web, mobile, Postman) can consume. FastAPI also auto-generates interactive docs at `/docs` (Swagger UI) and `/redoc` — so we get a free visual interface for testing as we build.

**Core Tech Stack:**

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.11+ | Type hints are heavily used |
| Framework | FastAPI | ASGI, async-first |
| ASGI Server | Uvicorn | Runs FastAPI in development |
| Database | PostgreSQL (local) | Relational, robust for financial data |
| ORM | SQLAlchemy 2.x (async) | With async engine for non-blocking DB calls |
| Migrations | Alembic | SQLAlchemy's migration tool (no Flask-Migrate wrapper needed) |
| Schema Validation | Pydantic v2 | FastAPI's native validation layer |
| Auth | python-jose + passlib | JWT tokens + password hashing |
| Payment | Paystack API | Via httpx (async HTTP client) |
| Environment | python-dotenv + pydantic-settings | Type-safe env variable loading |
| Testing | Postman / HTTPie / FastAPI `/docs` | Interactive docs included free |

---

## 2. Conceptual Customer Journey

Understanding this journey is critical — it tells us exactly what backend logic we need.

### 2.1 Event Organizer Flow

```
Organizer registers
    → Organizer creates an event (name, date, venue, total tickets, ticket price)
        → Event is published (status: PUBLISHED)
            → Tickets become available for purchase
                → Organizer can view sales dashboard (tickets sold, revenue)
                    → Event ends → tickets invalidated
```

### 2.2 Customer (Ticket Buyer) Flow

```
Customer registers / logs in
    → Customer browses available events
        → Customer selects an event and chooses quantity of tickets
            → Customer initiates payment
                → System reserves tickets temporarily (PENDING state)
                    → Customer is redirected to Paystack payment page
                        → Customer completes payment on Paystack
                            ↓
                    [Two things happen simultaneously]
                            ↓
                    Paystack sends webhook → Our server confirms payment
                    Customer is redirected to callback URL → We verify payment
                            ↓
                → Tickets are CONFIRMED and issued (with unique ticket codes)
                    → Customer receives booking confirmation
                        → Customer can view their tickets
                            → Customer presents ticket code at event (QR / code lookup)
```

### 2.3 What Happens When Payment Fails?

```
Customer initiates payment
    → System reserves tickets (PENDING)
        → Payment fails / customer cancels
            → Webhook signals failure OR timeout occurs
                → Reserved tickets are released back to available pool
                    → Customer can retry
```

---

## 3. Platform Features & Scope

### Phase 1 — What We Build (Our Focus)

| Feature | Description |
|---|---|
| User Auth | Register, login, JWT access tokens |
| Event Management | Create, list, view events |
| Ticket Inventory | Track available vs sold tickets |
| Payment Initiation | Call Paystack to start a transaction |
| Payment Verification | Verify transaction after redirect |
| Webhook Handling | Receive and process Paystack events |
| Booking Records | Store confirmed bookings with ticket codes |
| Ticket Lookup | Retrieve a customer's tickets |

### Phase 2 — Concepts We Explore Along the Way

| Topic | Why It Matters |
|---|---|
| Idempotency | Prevent double-charging on retries |
| Race conditions | Two users buying the last ticket simultaneously |
| Webhook security | Validating Paystack's HMAC signature |
| Payment states | PENDING → SUCCESS / FAILED / ABANDONED |
| Reference generation | Unique, traceable transaction references |
| DB vs Paystack data | What lives where and why |
| Async error handling | FastAPI's HTTPException and exception handlers |
| Dependency injection | FastAPI's `Depends()` system for DB sessions, auth |
| Logging | Audit trail for payment events |

---

## 4. Backend Architecture

```
ticketflow/
│
├── app/
│   ├── main.py                  # FastAPI app entry point, router registration
│   ├── config.py                # Pydantic Settings — type-safe env loading
│   ├── database.py              # Async SQLAlchemy engine + session factory
│   ├── dependencies.py          # Shared FastAPI Depends() — DB session, current user
│   │
│   ├── models/                  # SQLAlchemy ORM models (DB table definitions)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── event.py
│   │   ├── booking.py
│   │   ├── payment.py
│   │   └── ticket.py
│   │
│   ├── schemas/                 # Pydantic schemas (request/response shape & validation)
│   │   ├── __init__.py
│   │   ├── user.py              # UserCreate, UserResponse, UserLogin
│   │   ├── event.py             # EventCreate, EventResponse, EventUpdate
│   │   ├── booking.py           # BookingCreate, BookingResponse
│   │   ├── payment.py           # PaymentInitResponse, PaymentVerifyResponse
│   │   └── ticket.py            # TicketResponse
│   │
│   ├── routers/                 # FastAPI APIRouter — grouped route handlers
│   │   ├── __init__.py
│   │   ├── auth.py              # POST /auth/register, POST /auth/login
│   │   ├── events.py            # GET/POST/PATCH /events
│   │   ├── bookings.py          # POST/GET /bookings
│   │   ├── payments.py          # POST/GET /payments
│   │   └── webhooks.py          # POST /webhooks/paystack
│   │
│   ├── services/                # Business logic (kept separate from route handlers)
│   │   ├── paystack.py          # Async Paystack API wrapper (httpx)
│   │   ├── booking_service.py   # Booking + ticket reservation logic
│   │   └── ticket_service.py    # Ticket code generation + issuance
│   │
│   └── utils/
│       ├── security.py          # Password hashing, JWT creation/decoding
│       └── helpers.py           # Reference generators, formatters
│
├── alembic/                     # Alembic migration environment
│   ├── env.py                   # Alembic config — points to our models
│   ├── script.py.mako
│   └── versions/                # Auto-generated migration scripts
│
├── alembic.ini                  # Alembic config file
├── .env                         # Environment variables (never commit)
├── .env.example                 # Template for env vars
├── requirements.txt
└── run.py                       # Uvicorn entry point
```

### Key FastAPI Architecture Concepts

**Schemas vs Models — This distinction is fundamental in FastAPI:**

| Layer | Tool | Purpose |
|---|---|---|
| `models/` | SQLAlchemy | Defines the DB table structure. What gets stored. |
| `schemas/` | Pydantic | Defines API shapes. What comes in (request) and goes out (response). |

You will always have *two representations* of each entity. For example, a `User`:
- `models/user.py` → the DB table with `password_hash`, `created_at`, etc.
- `schemas/user.py` → `UserCreate` (email + password), `UserResponse` (id + email, **no password hash**)

This separation is intentional and critical for security — Pydantic schemas are your firewall between raw DB data and what the API exposes.

**`Depends()` — FastAPI's Dependency Injection:**

FastAPI uses `Depends()` to inject reusable logic into route handlers. We'll use this for:
- Getting a DB session per request (auto-closed after)
- Getting the currently authenticated user from the JWT token
- Role checking (is this user an organizer?)

```python
# Every protected route will look like this:
@router.post("/events")
async def create_event(
    event_data: EventCreate,           # Pydantic validates the request body
    db: AsyncSession = Depends(get_db),        # DB session injected
    current_user: User = Depends(get_current_user)  # Auth injected
):
    ...
```

---

## 5. API Endpoints Map

### Auth
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Register a new user |
| POST | `/auth/login` | No | Login, receive JWT access token |

### Events
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| GET | `/events` | No | List all published events |
| GET | `/events/{event_id}` | No | Get single event detail |
| POST | `/events` | Yes (organizer) | Create a new event |
| PATCH | `/events/{event_id}` | Yes (organizer) | Update event details |

### Bookings
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| POST | `/bookings` | Yes | Initiate a booking (reserves tickets) |
| GET | `/bookings/{booking_id}` | Yes | Get a specific booking |
| GET | `/bookings/me` | Yes | Get all bookings for current user |

### Payments
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| POST | `/payments/initialize` | Yes | Initialize Paystack transaction for a booking |
| GET | `/payments/verify/{reference}` | Yes | Manually verify a transaction by reference |
| GET | `/payments/callback` | No | Paystack redirect callback handler |

### Webhooks
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| POST | `/webhooks/paystack` | No (HMAC validated) | Receive Paystack event notifications |

> **Note on `/docs`:** FastAPI automatically generates Swagger UI at `http://localhost:8000/docs`. Every endpoint above will appear there with full request/response schemas — no extra work needed.

---

## 6. Database Design

> **Money Rule:** All monetary values are stored as **integers in the smallest currency unit** (kobo for NGN, pesewas for GHS). Never use floats for money — floating point precision errors are catastrophic in financial systems. `500000` kobo = `5000.00` NGN.

### Users Table
```
users
├── id (UUID, PK, default: uuid4)
├── email (String, unique, not null, indexed)
├── password_hash (String, not null)
├── full_name (String, not null)
├── role (Enum: customer | organizer | admin, default: customer)
├── is_active (Boolean, default: True)
├── created_at (DateTime, default: utcnow)
└── updated_at (DateTime, onupdate: utcnow)
```

### Events Table
```
events
├── id (UUID, PK)
├── organizer_id (UUID, FK → users.id, not null)
├── title (String, not null)
├── description (Text)
├── venue (String, not null)
├── event_date (DateTime, not null)
├── total_tickets (Integer, not null)
├── available_tickets (Integer, not null)   ← decremented on booking
├── ticket_price (Integer, not null)        ← in kobo
├── currency (String, default: "NGN")
├── status (Enum: draft | published | cancelled | completed)
├── created_at (DateTime)
└── updated_at (DateTime)
```

### Bookings Table
```
bookings
├── id (UUID, PK)
├── user_id (UUID, FK → users.id, not null)
├── event_id (UUID, FK → events.id, not null)
├── quantity (Integer, not null)
├── total_amount (Integer, not null)        ← quantity × ticket_price, in kobo
├── status (Enum: pending | confirmed | cancelled | failed)
├── paystack_reference (String, unique)     ← generated before calling Paystack
├── created_at (DateTime)
└── updated_at (DateTime)
```

### Payments Table
```
payments
├── id (UUID, PK)
├── booking_id (UUID, FK → bookings.id, not null)
├── paystack_reference (String, unique, not null)
├── paystack_transaction_id (String)        ← Paystack's own internal ID
├── amount (Integer, not null)              ← in kobo
├── currency (String)
├── status (Enum: pending | success | failed | abandoned)
├── payment_channel (String)               ← card | bank_transfer | ussd | mobile_money
├── paid_at (DateTime, nullable)           ← timestamp from Paystack on success
├── paystack_response (JSON)               ← full raw Paystack payload stored here
├── created_at (DateTime)
└── updated_at (DateTime)
```

### Tickets Table
```
tickets
├── id (UUID, PK)
├── booking_id (UUID, FK → bookings.id, not null)
├── user_id (UUID, FK → users.id, not null)
├── event_id (UUID, FK → events.id, not null)
├── ticket_code (String, unique, not null)  ← generated by us on payment confirmation
├── status (Enum: active | used | cancelled)
├── issued_at (DateTime)
└── updated_at (DateTime)
```

> **Why separate Bookings and Payments?**
> A booking represents the customer's *intent* to attend. A payment represents the *financial transaction*. A single booking can have multiple payment attempts (first card declined, retry with another). Keeping them separate gives you a clean audit trail and lets you re-try payment without creating a duplicate booking.

---

## 7. Paystack Ecosystem Concepts

### 7.1 API Keys
| Key | Use | Where It Lives |
|---|---|---|
| Secret Key (`sk_test_...`) | All server-side API calls. **Never expose.** | `.env` → loaded via pydantic-settings |
| Public Key (`pk_test_...`) | Frontend/client initialization only | Can be sent in API response |

### 7.2 Transaction Lifecycle

```
Your server calls /transaction/initialize
    → Paystack returns { authorization_url, reference, access_code }
        → Customer is redirected to authorization_url
            → Customer pays (or fails/abandons)
                → Paystack redirects customer back to your callback_url
                → Paystack independently POSTs to your webhook_url
                    ↓
            Your server calls /transaction/verify/:reference
                → Paystack returns final status: SUCCESS | FAILED | ABANDONED
```

Key states:
- **`pending`** — Transaction initialized, customer hasn't acted yet
- **`success`** — Payment completed and confirmed
- **`failed`** — Payment attempted but declined
- **`abandoned`** — Customer closed the page without paying

### 7.3 Paystack Webhook Event Types

| Event | Meaning | Our Action |
|---|---|---|
| `charge.success` | Payment completed successfully | Confirm booking, issue tickets |
| `charge.failed` | Payment failed | Mark booking failed, release tickets |
| `transfer.success` | Bank transfer payout succeeded | (Future: organizer payouts) |
| `transfer.failed` | Payout failed | (Future: retry or alert) |
| `subscription.create` | New subscription started | (Future: recurring tickets) |

### 7.4 Paystack Metadata
When initializing a transaction, pass a `metadata` object to embed your internal IDs. Paystack echoes this back in the webhook payload — this is how you reconnect the payment to your booking without storing extra lookup tables:

```json
{
  "email": "customer@example.com",
  "amount": 500000,
  "reference": "TKF-20240428-A1B2C3",
  "callback_url": "https://yourapi.com/payments/callback",
  "metadata": {
    "booking_id": "uuid-of-booking",
    "user_id": "uuid-of-user",
    "event_id": "uuid-of-event",
    "quantity": 2,
    "custom_fields": [
      { "display_name": "Event", "variable_name": "event_title", "value": "Lagos Music Fest" }
    ]
  }
}
```

### 7.5 The Reference Field
The `reference` is the most important field in a Paystack integration. It is the unique string that ties your booking to Paystack's transaction record.

- **You generate it** before calling Paystack (recommended — gives you control)
- It must be **unique per transaction**
- Format recommendation: `TKF-{YYYYMMDD}-{6-char-random}` e.g. `TKF-20240428-X7K2P1`
- You use it to **verify** the payment after the callback redirect
- Paystack echoes it in the **webhook** payload

---

## 8. Data Balancing: Your DB vs Paystack

This is one of the most important concepts in payment integration.

### What Lives in YOUR Database

| Data | Reason |
|---|---|
| Booking intent & status | Your business logic owns this |
| Ticket inventory (`available_tickets`) | You control availability, Paystack doesn't know about tickets |
| Ticket codes | Generated by you on confirmation |
| User records & roles | Your platform's domain |
| Event details | Your platform's domain |
| Payment status (mirrored) | Fast queries without hitting Paystack API on every request |

### What Lives in PAYSTACK (Their System)

| Data | Reason |
|---|---|
| Actual card/bank details | PCI compliance — you must never touch or store these |
| Authorization codes | Stored by Paystack for recurring charge capability |
| Full transaction ledger | Paystack's financial source of truth |
| Dispute/chargeback records | Handled entirely by Paystack |
| Settlement reports | Paystack manages payout scheduling |

### What You Store FROM Paystack (Mirror in Your DB)

| Field | Column in `payments` table | Why Store It |
|---|---|---|
| `reference` | `paystack_reference` | The link between your booking and Paystack's record |
| `id` (Paystack's) | `paystack_transaction_id` | For direct lookup in Paystack dashboard |
| `status` | `status` | Avoid calling Paystack API for every status check |
| `paid_at` | `paid_at` | Exact timestamp of successful charge |
| `channel` | `payment_channel` | Useful for analytics (card vs USSD vs bank) |
| `authorization.authorization_code` | (future) | Enables charging the card again without re-entry |
| Full response body | `paystack_response` (JSON column) | Complete audit trail — critical for disputes |

### The Golden Rule
> **Your DB is the source of truth for business logic (bookings, tickets, users). Paystack is the source of truth for financial transactions. When they conflict — trust Paystack, then update your DB.**

### Practical Example of Conflict Resolution
```
Scenario: Webhook arrives saying charge.success,
          but your DB still shows booking.status = "pending"

Correct action:
  1. Verify the reference with Paystack API (/transaction/verify)
  2. Paystack confirms success → update booking to "confirmed"
  3. Issue tickets
  4. Log the discrepancy

Wrong action:
  Ignore the webhook because "the DB says pending"
```

---

## 9. Key Backend Topics We Will Cover

### Section A — Project Setup
- FastAPI app instantiation and lifespan events
- Async SQLAlchemy engine setup (`create_async_engine`)
- `pydantic-settings` for type-safe `.env` loading
- Alembic initialization and configuration
- Uvicorn as the ASGI server

### Section B — Models & Schemas (The FastAPI Way)
- SQLAlchemy 2.x declarative models with type annotations
- UUID primary keys with `uuid4` defaults
- SQLAlchemy `Enum` types mapped to PostgreSQL enums
- `relationship()` and `ForeignKey` in async context
- Pydantic v2 schemas: `BaseModel`, `model_config`, `ConfigDict`
- `UserCreate` vs `UserResponse` — why you always have two schemas per entity
- Storing money as integers (never floats!)

### Section C — Async Database Sessions
- `AsyncSession` and `async_sessionmaker`
- The `get_db` dependency — request-scoped session with `Depends()`
- Why async DB matters for payment integrations (non-blocking I/O)
- Alembic migrations: `alembic revision --autogenerate` and `alembic upgrade head`

### Section D — Auth
- Password hashing with `passlib` (bcrypt)
- JWT creation and decoding with `python-jose`
- `OAuth2PasswordBearer` — FastAPI's built-in token scheme
- `get_current_user` dependency — reused across all protected routes
- Role-based access with a `require_role()` dependency factory

### Section E — Events API
- FastAPI `APIRouter` — grouping related routes
- Path parameters `{event_id}` vs query parameters `?status=published`
- Response models — `response_model=EventResponse` auto-filters output
- Status codes — `status_code=201` for creation, `404` with `HTTPException`

### Section F — Booking & Payment Initiation
- Ticket reservation logic with `SELECT ... FOR UPDATE` (pessimistic locking)
- Why we need locking: the race condition explained
- Generating unique Paystack references
- Calling Paystack `POST /transaction/initialize` with `httpx.AsyncClient`
- What to persist in DB *before* redirecting the user (and why)
- Returning `authorization_url` to the client

### Section G — Payment Callback & Verification
- The callback URL flow — what Paystack sends in the redirect
- Why callback alone is not enough (browser can be closed)
- Server-side verification: `GET /transaction/verify/{reference}`
- Updating `booking.status` and `payment.status` atomically
- Issuing tickets only after confirmed payment

### Section H — Webhooks
- Why webhooks are more reliable than callbacks
- FastAPI `Request` object — reading raw body for HMAC validation
- HMAC-SHA512 signature validation with Python's `hmac` module
- Idempotency: checking if a webhook event was already processed
- Processing `charge.success`: confirm booking + issue tickets
- Processing `charge.failed`: release reserved tickets
- Returning `200 OK` immediately (Paystack retries on non-200)

### Section I — Error Handling & Edge Cases
- FastAPI `HTTPException` vs custom exception handlers
- `@app.exception_handler()` for global error formatting
- What if Paystack is down? Timeout handling with `httpx`
- What if webhook arrives before callback? (idempotency saves you)
- What if a user pays twice for the same booking? (reference uniqueness)
- Stale PENDING bookings — background cleanup task with `asyncio`

### Section J — Logging & Audit Trail
- Python `logging` module in async context
- Structured logging for payment events
- Storing raw Paystack JSON responses (the `paystack_response` column)
- Building a simple payment lookup endpoint for debugging

---

## 10. Build Sequence (Section by Section)

We build in this exact order, one small segment at a time:

```
Step 01 → Project structure & virtual environment setup
Step 02 → FastAPI app entry point + Uvicorn runner
Step 03 → pydantic-settings config (type-safe .env loading)
Step 04 → Async SQLAlchemy engine + session + get_db dependency
Step 05 → Alembic setup + first migration (empty)
Step 06 → User model (SQLAlchemy) + User schemas (Pydantic)
Step 07 → Alembic migration for users table
Step 08 → Auth utilities (password hash, JWT create/decode)
Step 09 → Auth router (POST /auth/register + POST /auth/login)
Step 10 → get_current_user dependency + role checking
Step 11 → Event model + Event schemas
Step 12 → Events router (CRUD endpoints)
Step 13 → Booking + Ticket + Payment models
Step 14 → Alembic migration for all new tables
Step 15 → Paystack service (async httpx wrapper)
Step 16 → Booking router (initiate booking + reserve tickets)
Step 17 → Payment initialization route (call Paystack, store payment record)
Step 18 → Payment callback handler (GET /payments/callback)
Step 19 → Payment verification route (GET /payments/verify/{reference})
Step 20 → Ticket issuance service (generate codes on confirmation)
Step 21 → Webhook router (HMAC validation + charge.success/failed handlers)
Step 22 → My bookings + ticket lookup endpoints
Step 23 → Edge case hardening (timeouts, duplicate webhooks, stale bookings)
Step 24 → Logging & audit trail
```

---

## 11. Environment & Tools Setup

### Prerequisites
- Python 3.11+
- PostgreSQL installed and running locally
- A Paystack account (free at [paystack.com](https://paystack.com)) — use **Test Mode**
- Postman, Insomnia, or FastAPI's built-in `/docs` for API testing
- **ngrok** (free) — exposes your `localhost` to the internet so Paystack can send webhooks during development

### Required Python Packages
```txt
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
asyncpg
alembic
pydantic[email]
pydantic-settings
passlib[bcrypt]
python-jose[cryptography]
httpx
python-dotenv
```

> **Why `asyncpg` instead of `psycopg2`?**
> `asyncpg` is the async PostgreSQL driver. Since we're using SQLAlchemy's async engine, we need an async-compatible driver. `psycopg2` is synchronous and would block the event loop.

### Environment Variables (`.env`)
```env
# App
APP_ENV=development
SECRET_KEY=your-super-secret-key-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/ticketflow_db

# Paystack
PAYSTACK_SECRET_KEY=your_paystack_secret_key_here
PAYSTACK_PUBLIC_KEY=your_paystack_public_key_here
PAYSTACK_BASE_URL=https://api.paystack.co

# URLs
CALLBACK_URL=http://localhost:8000/payments/callback
WEBHOOK_URL=https://your-ngrok-subdomain.ngrok.io/webhooks/paystack
```

> **Note on `DATABASE_URL`:** FastAPI with async SQLAlchemy requires the `postgresql+asyncpg://` prefix (not just `postgresql://`). This tells SQLAlchemy to use the `asyncpg` driver.

### Paystack Test Cards
| Card Number | Expiry | CVV | OTP | Result |
|---|---|---|---|---|
| 4084 0840 8408 4081 | Any future date | Any 3 digits | `408408` | ✅ Success |
| 4084 0840 8408 4084 | Any future date | Any 3 digits | — | ❌ Decline |
| 5531 8866 5214 2950 | 09/32 | 564 | `408408` | ✅ Success (Mastercard) |

### Setting Up ngrok for Webhooks
```bash
# Install ngrok, then:
ngrok http 8000

# You'll get a URL like:
# https://a1b2c3d4.ngrok.io

# Set this in your .env:
WEBHOOK_URL=https://a1b2c3d4.ngrok.io/webhooks/paystack

# Register it in Paystack Dashboard:
# Settings → API Keys & Webhooks → Webhook URL
```

---

## 12. Why FastAPI for This Project

Understanding *why* we chose FastAPI shapes how we write code throughout.

| Feature | Benefit for Payment Integration |
|---|---|
| **Async-first** | Non-blocking calls to Paystack API and DB simultaneously |
| **Pydantic validation** | Request bodies are validated before any business logic runs — invalid data never reaches your payment code |
| **Auto-generated `/docs`** | Interactive Swagger UI for testing every endpoint — no Postman setup needed to get started |
| **`Depends()` system** | DB sessions, auth, and role checks are injected cleanly — no global state |
| **Type hints everywhere** | Catches bugs at development time, not at payment time |
| **`HTTPException`** | Standardized error responses — Paystack errors get clean 4xx/5xx responses |
| **Background tasks** | `BackgroundTasks` can send confirmation emails after ticket issuance without blocking the response |

### FastAPI vs Flask — The Key Differences You'll Notice

| Concept | Flask | FastAPI |
|---|---|---|
| Routing | `@app.route()` | `@router.get()`, `@router.post()` etc. |
| Request body | `request.get_json()` | Pydantic model as function parameter |
| Validation | Manual or via marshmallow | Automatic via Pydantic |
| Auth injection | Custom decorator | `Depends(get_current_user)` |
| DB session | `g` object or context | `Depends(get_db)` |
| Async support | Limited (needs workarounds) | Native `async def` routes |
| API docs | External (Swagger separate) | Built-in at `/docs` |
| Response shaping | `jsonify()` | `response_model=` parameter |

---

## Let's Begin

With this blueprint in place, we have a clear map of:

- **What** we're building — an event ticketing backend (TicketFlow)
- **Why** each component exists — the customer journey drives every decision
- **How** FastAPI and Paystack interact — async calls, dependency injection, webhook handling
- **When** to trust which system — your DB for business logic, Paystack for financial truth
- **What's different** about FastAPI — schemas, `Depends()`, async sessions, Pydantic

**Next step → Step 01: Project structure & virtual environment setup.**

Say the word and we start with the first segment of code.
