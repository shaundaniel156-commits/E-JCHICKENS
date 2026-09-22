# E&J's CHICKENS — System Architecture & Implementation Plan

## 1. Purpose

A production-oriented poultry farm management system. Every number the user sees is
**derived from recorded transactions** — nothing on the dashboard is hard-coded or
manually typed in as a summary.

## 2. Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite, React Router 6, Recharts, Lucide React, plain CSS design tokens |
| Backend | Python 3.11 + FastAPI, layered (router → service → repository → model) |
| Database | MySQL 8 / MariaDB 10.11, SQLAlchemy 2.0 ORM, Alembic migrations |
| Validation | Pydantic v2 (backend), mirrored lightweight validation in the UI |
| Auth | JWT access + refresh tokens, bcrypt password hashing, RBAC |
| Money | `DECIMAL(16,2)` in MySQL, `decimal.Decimal` in Python, serialized as JSON strings |

## 3. Layering rules

```
routers/       HTTP surface only: status codes, dependencies, response models
services/      business rules, calculations, transactions, notifications, audit
repositories/  query construction + persistence (no business rules)
models/        SQLAlchemy ORM entities + constraints
schemas/       Pydantic request/response contracts
```

A router never touches a `Session.query`; a repository never decides policy.

## 4. Data model

### Identity & audit
- `roles` — ADMIN / MANAGER / STAFF (seeded, referenced by `users.role_id`)
- `users` — email + username unique, `password_hash`, `is_active`, `last_login_at`
- `activity_logs` — user, action, module, description, entity id, IP, timestamp
- `notifications` — type, severity, title, message, module, entity id, read flag

### Flock
- `bird_batches` — `batch_code` (unique), breed, `initial_quantity`, `acquisition_date`,
  source, `age_days_at_acquisition`, `cost_per_bird`, `adjustment_quantity`, status, notes
- `mortality_records` — batch, date, quantity, cause, notes
- `health_records` — batch, date, `sick_count`, symptoms, diagnosis, treatment,
  medicine, dosage, `treatment_cost`, vet name, status

### Feed
- `feed_types` — name (unique), description, `default_bag_weight_kg`
- `feed_purchases` — feed type, date, brand, bags, bag weight, cost/bag, total cost,
  supplier, lot number
- `feed_consumption` — feed type, batch, date, bags, kg, notes

### Money
- `expense_categories` — name (unique), colour token, system flag
- `expenses` — date, category, description, amount, vendor, payment method, reference,
  `source_type`/`source_id` for auto-generated entries
- `customers` — name (unique), phone, email, address
- `sales` — date, batch, customer, quantity, unit price, total, payment status/method,
  `amount_paid`
- `budgets` — name, amount, start/end date, active flag
- `farm_settings` — single row: farm identity, currency, date format, alert thresholds

### Derived quantities (never stored)

```
batch.total_deaths        = Σ mortality.quantity        (batch, not deleted)
batch.total_sold          = Σ sales.quantity            (batch, not deleted, not cancelled)
batch.current_quantity    = initial_quantity − deaths − sold − adjustment_quantity
batch.sick_count          = Σ health.sick_count where status ∈ (SICK, UNDER_TREATMENT, CRITICAL)
batch.mortality_rate      = deaths / (initial_quantity − adjustment_quantity) × 100

feed.stock_kg             = Σ purchases.quantity_kg − Σ consumption.quantity_kg
feed.stock_bags           = stock_kg / feed_type.default_bag_weight_kg

revenue (accrual)         = Σ sales.total_amount        (not cancelled, not deleted)
cash_collected            = Σ sales.amount_paid
total_expenses            = Σ expenses.amount           (not deleted)
net_profit_or_loss        = revenue − total_expenses
net_cash_position         = cash_collected − total_expenses
budget_remaining          = budget.amount − expenses within the budget period
```

`budget_remaining` is deliberately **not** profit: the Finance page shows both side by
side with distinct labels and colours.

## 5. Integrated data flow (single entry, system-wide effect)

| User action | Automatic consequences |
|---|---|
| Create bird batch | Expense auto-created (category *Birds*, `source_type=bird_batch`), activity log, dashboard bird count rises |
| Record mortality | Batch current quantity falls, mortality rate recalculated, high-mortality notification, activity log |
| Record health record | Sick count rises; if `treatment_cost > 0` an expense is auto-created (*Medicine*), notification + activity log |
| Purchase feed | Feed stock rises, expense auto-created (*Feed*), activity log |
| Record consumption | Feed stock falls; low-stock notification when below threshold |
| Record sale | Stock check → birds fall, revenue rises, profit/loss updates, notification + activity log |
| Add expense | Total expenses rise, budget remaining falls, budget-threshold notification, profit/loss updates |

Auto-generated expenses carry `source_type`/`source_id`; they cannot be edited or deleted
directly — the source record owns them, so the two modules can never disagree.

## 6. Integrity rules

- Mortality + sales are validated against **live** batch availability inside the same
  transaction; over-selling or over-recording deaths returns `409 Conflict`.
- Feed consumption is validated against live stock for that feed type (`409` when short).
- Quantities and money are non-negative (Pydantic constraints + MySQL `CHECK`).
- Financial and flock records use **soft delete** (`is_deleted`, `deleted_at`, `deleted_by`)
  so history is never silently lost. Deleting a sale releases the birds again because
  availability is derived, not stored.
- All writes run inside one `Session` transaction, committed once by the service.

## 7. Security

bcrypt hashing, JWT access (short-lived) + refresh tokens, role dependencies
(`require_roles`), protected React routes, CORS allow-list from env, ORM-parameterised SQL,
no secrets in the repository (`.env.example` only), sanitized error responses with full
detail written to the server log.

## 8. API surface

`/api/v1` + `auth, users, birds, mortality, health, feed, expenses, sales, budgets,
finance, dashboard, reports, notifications, activity, settings`. OpenAPI at `/docs`.

## 9. Build phases

1. Architecture (this document)
2. Database models + Alembic migration
3. Backend: core → models → schemas → repositories → services → routers
4. Frontend: design system → layout → auth → dashboard → modules
5. Integration: remove all mock data, wire every page to the API
6. Testing: pytest suite for calculations, permissions, validation; live end-to-end run
7. Polish: responsiveness, empty/loading/error states, accessibility
8. Final acceptance run of the 28-step scenario in the brief
