# E&J's CHICKENS — Poultry Farm Management System

A complete, working farm-management application: flock, feed, health, mortality,
sales, expenses, budgets, reports and notifications in one system.

**The guiding principle: data entered once flows through the entire system.**
Record a sale and the birds leave the batch, revenue rises, profit is
recalculated, the reports change, a notification is raised and the audit log
grows — all from that single entry. No figure on any screen is typed in as a
summary or hard-coded; every number is derived from recorded transactions.

---

---

## Quickest way to see it running

> **A note first:** opening `frontend/index.html` by double-clicking it shows a
> **blank white page**. That is expected — it is not a broken file. This is a
> React application, so its code has to be compiled and served by a small local
> web server before a browser can display anything. The steps below do that for
> you.

### Windows

1. Install **[Python 3.11+](https://www.python.org/downloads/)** — on the first
   installer screen, tick **"Add python.exe to PATH"**.
2. Install **[Node.js LTS](https://nodejs.org/)** — just click through.
3. Double-click **`setup.bat`** and wait. It builds everything and adds demo
   data. You only ever do this once.
4. Double-click **`start.bat`**. Two windows open and your browser goes to the app.

### macOS / Linux

```bash
bash setup.sh     # once
bash start.sh     # every time you want to run it
```

Then sign in at **<http://localhost:5173>**:

| Email | Password |
|---|---|
| `admin@ejchickens.com` | `Admin@12345` |

**You do not need to install MySQL to review the project.** The setup scripts
use SQLite, which needs no server and no configuration, and the application
behaves identically. When you are ready to run the farm for real, switch
`DATABASE_URL` in `backend/.env` to MySQL — see [Installation](#installation).

To stop the app: close the two windows (Windows), or press `Ctrl+C` (macOS/Linux).

---

## Table of contents

1. [Quickest way to see it running](#quickest-way-to-see-it-running)
2. [Features](#features)
3. [Technology stack](#technology-stack)
4. [System architecture](#system-architecture)
5. [How the numbers are calculated](#how-the-numbers-are-calculated)
6. [Installation](#installation)
7. [Running the application](#running-the-application)
8. [Seed data and default credentials](#seed-data-and-default-credentials)
9. [Testing](#testing)
10. [API documentation](#api-documentation)
11. [Project structure](#project-structure)
12. [Troubleshooting](#troubleshooting)

---

## Features

### Flock
- Multiple bird batches, each tracked separately (code, breed, source, age, cost)
- Live population per batch: **initial − deaths − sold − other losses**
- Mortality recording with cause, plus mortality rate and high-mortality alerts
- Health records: symptoms, diagnosis, treatment, medicine, dosage, cost, vet,
  and a status of Sick / Under treatment / Critical / Recovered
- Non-mortality losses (theft, escape, corrected miscount) recorded separately so
  they never distort the mortality rate

### Feed
- Feed types with their usual bag weight
- Purchases (bags, bag weight, cost per bag, supplier, lot number)
- Consumption entered in **either bags or kilograms**, converted automatically
- Running stock per feed type, with low-stock alerts; stock can never go negative

### Money
- Expenses across 16 categories, with supplier, payment method, reference and
  receipt link
- Budgets with spent / remaining / percentage and warning + exceeded alerts
- Sales with customers, unit price, automatic totals, and full/partial/unpaid
  payment tracking
- A Finance page that keeps **budget remaining** and **profit** visibly separate

### Everywhere
- Dashboard with live summary cards and six charts
- Six reports, each exportable to **CSV and PDF**
- Automatic notifications (low feed, high mortality, budget limits, sales, health)
- Full activity/audit log with user, action, module and timestamp
- Role-based access: Administrator, Farm Manager, Staff
- Search, filtering, sorting, pagination and date-range filters on every list
- Soft deletion of financial and flock records, so history is reversed, not erased
- Responsive from desktop to phone, with light and dark themes

---

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 5, React Router 6, Recharts, Lucide React |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Database | MySQL 8 (MariaDB 10.11 also works), SQLAlchemy 2.0, Alembic |
| Validation | Pydantic v2 |
| Auth | JWT access + refresh tokens, bcrypt password hashing |
| Reports | ReportLab (PDF), Python `csv` (Excel-compatible CSV) |
| Tests | pytest + FastAPI TestClient |

---

## System architecture

```
                  Browser (React + Vite)
                          │  JSON over HTTPS, Bearer token
                          ▼
   ┌──────────────────────────────────────────────┐
   │ FastAPI                                      │
   │  routers/       HTTP surface, status codes   │
   │  dependencies/  auth + role guards, filters  │
   │  services/      business rules, transactions │
   │  repositories/  queries and aggregates       │
   │  models/        SQLAlchemy entities          │
   │  schemas/       Pydantic request/response    │
   └──────────────────────────────────────────────┘
                          │  SQLAlchemy ORM
                          ▼
                  MySQL (16 tables)
```

A router never writes a query; a repository never decides policy. Each service
call runs in one transaction and commits once, so a half-finished sale can never
be left in the database.

**Database tables:** `roles`, `users`, `farm_settings`, `bird_batches`,
`mortality_records`, `health_records`, `feed_types`, `feed_purchases`,
`feed_consumption`, `expense_categories`, `expenses`, `customers`, `sales`,
`budgets`, `notifications`, `activity_logs`.

A fuller design note lives in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## How the numbers are calculated

Nothing below is stored as a running total — each is computed from the records
every time it is asked for, which is why the modules can never disagree.

```
batch.current_quantity = initial_quantity − deaths − sold − other_losses
farm total birds       = Σ current_quantity over all batches
mortality_rate         = deaths ÷ (initial_quantity − other_losses) × 100
sick birds             = Σ sick_count of OPEN health records only
                         (Recovered records stop counting, so no double counting)

feed stock (kg)        = Σ purchased kg − Σ consumed kg
feed stock (bags)      = stock_kg ÷ the feed type's bag weight

total revenue          = Σ sale totals   (excluding cancelled and reversed sales)
cash collected         = Σ amounts actually paid
total expenses         = Σ expenses      (excluding reversed ones)

net profit or loss     = total revenue − total expenses
net cash position      = cash collected − total expenses
budget remaining       = budget amount − expenses dated inside the budget period
```

### Budget remaining is **not** profit

The brief is emphatic about this, and so is the interface. Using the worked
example:

| Figure | Amount |
|---|---|
| Budget | UGX 1,000,000 |
| Expenses | UGX 800,000 |
| **Budget remaining** | **UGX 200,000** — what you may still spend |
| Revenue | UGX 1,200,000 |
| **Net profit** | **UGX 400,000** — revenue less expenses |

Both appear on the Finance page side by side, under separate headings, and the
difference is spelled out on screen.

### Entering data once

| What you record | What happens automatically |
|---|---|
| A bird batch | An expense is created under *Birds*; the dashboard count rises |
| A feed purchase | Stock rises; an expense is created under *Feed* |
| Feed consumption | Stock falls; a low-stock alert fires if it drops below the threshold |
| A health record with a treatment cost | An expense is created under *Medicine* |
| Mortality | The batch population falls; a high-mortality alert may fire |
| A sale | Birds leave the batch, revenue rises, profit updates, a notification is raised |
| Any expense | The budget remaining falls; a budget alert may fire |

Automatically created expenses are marked in the Expenses list and cannot be
edited there — you edit the record they came from, so the two can never drift
apart.

---

## Installation

### Prerequisites

| Software | Version | Check with |
|---|---|---|
| Python | 3.11 or newer | `python3 --version` |
| Node.js | 18 or newer | `node --version` |
| MySQL | 8.0 (or MariaDB 10.6+) | `mysql --version` |
| Git | any recent | `git --version` |

### 1. Get the code

```bash
git clone <your-repository-url>
cd ShapeHierarchy
```

> If you only want to look at the project, skip to
> [Quickest way to see it running](#quickest-way-to-see-it-running) — it needs no
> MySQL. The steps below are for running the farm on MySQL properly.

### 2. Create the MySQL database

Sign in to MySQL as an administrator:

```bash
mysql -u root -p
```

Then run:

```sql
CREATE DATABASE ej_chickens CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE ej_chickens_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'ejfarm'@'localhost' IDENTIFIED BY 'choose-a-strong-password';
GRANT ALL PRIVILEGES ON ej_chickens.*      TO 'ejfarm'@'localhost';
GRANT ALL PRIVILEGES ON ej_chickens_test.* TO 'ejfarm'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

`ej_chickens_test` is only needed if you want to run the test suite against
MySQL; the tests use a temporary SQLite file by default.

### 3. Set up the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Now open `backend/.env` and fill in two values:

```ini
# Use the user and password you created above
DATABASE_URL=mysql+pymysql://ejfarm:choose-a-strong-password@localhost:3306/ej_chickens

# Generate a long random key — never leave this at its default
JWT_SECRET_KEY=paste-a-long-random-string-here
```

Generate a key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Every environment variable is documented in `backend/.env.example`.

### 4. Create the database tables

```bash
alembic upgrade head        # builds the schema
python -m app.db.init_db    # roles, categories, feed types, first administrator
```

`init_db` creates the first administrator from these optional environment
variables (defaults in brackets):

```
ADMIN_EMAIL     [admin@ejchickens.com]
ADMIN_USERNAME  [admin]
ADMIN_PASSWORD  [Admin@12345]
ADMIN_NAME      [Farm Administrator]
```

**Set `ADMIN_PASSWORD` before running this on a real farm**, or sign in and
change the password immediately.

### 5. Set up the frontend

```bash
cd ../frontend
npm install
cp .env.example .env
```

The defaults work for local development — the Vite dev server proxies `/api` to
`http://127.0.0.1:8000`, so there is no CORS setup to do.

---

## Running the application

Open two terminals.

**Terminal 1 — backend:**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

Then open **<http://localhost:5173>**.

| What | Where |
|---|---|
| Application | http://localhost:5173 |
| API | http://127.0.0.1:8000/api/v1 |
| Interactive API docs | http://127.0.0.1:8000/docs |
| Health check | http://127.0.0.1:8000/health |

### Building for production

```bash
cd frontend && npm run build        # output in frontend/dist/
```

Serve `frontend/dist/` with any static web server, set `VITE_API_BASE_URL` to
your API's public URL before building, and run the backend behind a process
manager:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

In production set `APP_ENV=production` and `DEBUG=false`, and list your real
frontend origin in `CORS_ORIGINS`.

### Database migrations

```bash
alembic upgrade head                              # apply all migrations
alembic revision --autogenerate -m "describe it"  # after changing a model
alembic downgrade -1                              # step back one migration
alembic current                                   # what is applied now
```

---

## Seed data and default credentials

> **The seed data is fictional sample data for development and demonstrations.**
> Do not run it against a real farm's database.

```bash
cd backend
source .venv/bin/activate
python -m app.db.seed            # add demo data
python -m app.db.seed --reset    # wipe everything first, then add demo data
```

This creates three bird batches, feed purchases and consumption, health records,
mortality, a budget, fifteen expenses, three customers and six sales — enough for
every chart and report to have something to show.

### Development accounts

| Email | Password | Role |
|---|---|---|
| `admin@ejchickens.com` | `Admin@12345` | Administrator (created by `init_db`) |
| `esther@ejchickens.com` | `Esther@12345` | Administrator (seed data) |
| `james@ejchickens.com` | `James@12345` | Farm manager (seed data) |
| `grace@ejchickens.com` | `Grace@12345` | Staff (seed data) |

**Change these before the system is used on a real farm.**

### What each role can do

| | Administrator | Farm manager | Staff |
|---|:---:|:---:|:---:|
| Dashboard | ✅ | ✅ | ✅ |
| Birds — add a batch | ✅ | ✅ | ✕ |
| Birds — edit breed, source, age, notes | ✅ | ✅ | ✅ |
| Birds — edit quantity, cost, status | ✅ | ✅ | ✕ |
| Mortality, health, feed use | ✅ | ✅ | ✅ |
| Feed purchases | ✅ | ✅ | ✕ |
| Sales | ✅ | ✅ | ✕ |
| Expenses, Finance, Reports | ✅ | ✅ | ✕ |
| Budgets | ✅ | view | ✕ |
| Users, Activity log | ✅ | ✕ | ✕ |
| Settings | edit | view | view |

---

## Testing

```bash
cd backend
source .venv/bin/activate
pytest                 # 90 tests
pytest -v              # with test names
pytest tests/test_financial_calculations.py   # one file
```

Tests run against a temporary SQLite database by default, so no server is
needed. To run the identical suite against MySQL:

```bash
TEST_DATABASE_URL="mysql+pymysql://ejfarm:your-password@localhost:3306/ej_chickens_test" pytest
```

### What is covered

| File | Covers |
|---|---|
| `test_auth.py` | Hashing, login, tokens, refresh, password reset and change |
| `test_permissions.py` | What each role can and cannot reach |
| `test_bird_calculations.py` | Population arithmetic, mortality rate, reversals |
| `test_financial_calculations.py` | Budget, revenue, profit/loss, payment status |
| `test_feed.py` | Stock arithmetic, negative-stock guards, auto-expenses |
| `test_validation.py` | Every validation rule, rejected at the API |
| `test_integration.py` | Data flowing between modules; reports agreeing with the dashboard |
| `test_migrations.py` | `alembic upgrade head` runs on SQLite, and the migration matches the models |

The three worked examples from the specification are asserted directly:

```
500 birds − 20 deaths − 50 sales            → 430 birds
budget 1,000,000 − expenses 800,000         → 200,000 remaining
revenue 1,200,000 − expenses 800,000        → 400,000 profit
```

### Frontend checks

```bash
cd frontend
npm run build      # type-free build; fails on any import or syntax error
npm run lint       # ESLint
```

---

## API documentation

FastAPI generates interactive documentation at **<http://127.0.0.1:8000/docs>**.
Use `POST /api/v1/auth/login`, copy the `access_token`, click **Authorize** and
paste it to try any endpoint.

All routes are under `/api/v1`:

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `GET /auth/me`, `POST /auth/forgot-password`, `/auth/reset-password`, `/auth/change-password` |
| Dashboard | `GET /dashboard/summary` |
| Birds | `GET/POST /birds`, `GET/PUT/DELETE /birds/{id}`, `POST /birds/{id}/adjust`, `GET /birds/options` |
| Mortality | `GET/POST /mortality`, `PUT/DELETE /mortality/{id}`, `GET /mortality/series` |
| Health | `GET/POST /health-records`, `PUT/DELETE /health-records/{id}`, `GET /health-records/summary` |
| Feed | `GET /feed/stock`, `GET/POST /feed/types`, `GET/POST /feed/purchases`, `GET/POST /feed/consumption` (+ `PUT`/`DELETE` by id) |
| Expenses | `GET/POST /expenses`, `GET/PUT/DELETE /expenses/{id}`, `GET /expenses/categories`, `GET /expenses/breakdown` |
| Sales | `GET/POST /sales`, `GET/PUT/DELETE /sales/{id}`, `GET/POST /customers` |
| Finance | `GET /finance/summary`, `GET/POST /budgets`, `GET /budgets/active`, `PUT/DELETE /budgets/{id}` |
| Reports | `GET /reports/{birds,feed,expenses,sales,profit-loss,performance}`, `GET /reports/{report}/export?format=csv\|pdf` |
| Notifications | `GET /notifications`, `GET /notifications/count`, `POST /notifications/{id}/read`, `POST /notifications/read-all` |
| Users | `GET/POST /users`, `GET/PUT/DELETE /users/{id}`, `POST /users/{id}/reset-password`, `GET/PUT /users/me` |
| Activity | `GET /activity` |
| Settings | `GET/PUT /settings` |

**List endpoints** accept `page`, `page_size`, `search`, `sort`, `order`, plus
either `preset` (`today`, `yesterday`, `this_week`, `last_week`, `this_month`,
`last_month`, `this_year`, `all_time`) or an explicit `start_date`/`end_date`.

**Errors** always come back in the same shape:

```json
{ "error": { "code": "insufficient_stock",
             "message": "Batch BROILER-001 has only 42 bird(s) available.",
             "details": { "quantity": "..." } } }
```

| Status | Meaning |
|---|---|
| 400 / 422 | Invalid input (422 includes per-field messages) |
| 401 | Not signed in, or the token has expired |
| 403 | Signed in, but your role does not allow this |
| 404 | No such record |
| 409 | A business rule was broken — selling more birds than exist, feed going negative, a duplicate code |
| 503 | The database is unreachable |

Money crosses the API as an exact decimal **string** (`"800000.00"`), never a
floating-point number, so no rounding is introduced in transit.

---

## Project structure

```
.
├── backend/
│   ├── alembic/                   # database migrations
│   ├── app/
│   │   ├── core/                  # config, security, logging, error handling
│   │   ├── db/                    # engine, base classes, init_db, seed
│   │   ├── models/                # SQLAlchemy tables
│   │   ├── schemas/               # Pydantic request/response models
│   │   ├── repositories/          # queries and derived-figure helpers
│   │   ├── services/              # business rules (one per module)
│   │   ├── routers/               # HTTP endpoints
│   │   ├── dependencies/          # auth guards, pagination, date ranges
│   │   ├── utils/                 # money, dates, pagination, CSV/PDF export
│   │   └── main.py                # the FastAPI application
│   ├── tests/                     # pytest suite
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── public/logo.svg
│   ├── src/
│   │   ├── api/                   # HTTP client and endpoint wrappers
│   │   ├── components/            # UI primitives, DataTable, charts, filters
│   │   ├── contexts/              # auth, toasts, farm settings + theme
│   │   ├── hooks/                 # useApi, useListQuery, option loaders
│   │   ├── layouts/               # app shell, sidebar, top bar
│   │   ├── pages/                 # one file per screen
│   │   ├── styles/index.css       # design tokens and components
│   │   └── utils/format.js        # currency, dates, numbers
│   ├── .env.example
│   └── package.json
├── docs/ARCHITECTURE.md
└── README.md
```

---

## Troubleshooting

**I double-clicked `frontend/index.html` and got a blank white page**
That is expected, and nothing is broken. `index.html` loads `/src/main.jsx`,
which is React source code: browsers cannot run it directly, and a `file://`
page cannot load modules at all. The code has to be compiled and served. Use
`start.bat` (Windows) or `bash start.sh`, then open <http://localhost:5173>.

**Do I have to install MySQL just to look at the project?**
No. `setup.bat` / `setup.sh` configure SQLite, which is a single file and needs
no server. Every feature works the same way. Switch to MySQL only when you are
ready to run the farm for real.

**`Can't connect to MySQL server` / the health check says `unavailable`**
Make sure MySQL is running (`sudo systemctl start mysql`, or `brew services
start mysql`), then check `DATABASE_URL` in `backend/.env`. Test the credentials
directly: `mysql -u ejfarm -p ej_chickens`.

**`Access denied for user 'ejfarm'@'localhost'`**
The password in `DATABASE_URL` does not match the one you set. Re-run the
`CREATE USER` / `GRANT` statements above, or reset it with
`ALTER USER 'ejfarm'@'localhost' IDENTIFIED BY 'new-password';`.

**`Table 'ej_chickens.users' doesn't exist`**
The migrations have not been applied. Run `alembic upgrade head`, then
`python -m app.db.init_db`.

**`ModuleNotFoundError: No module named 'app'`**
Run backend commands from inside the `backend/` directory, with the virtual
environment activated.

**The frontend loads but every request fails**
The backend is not running, or is on a different port. Check
<http://127.0.0.1:8000/health>. If your API is elsewhere, set `VITE_API_TARGET`
in `frontend/.env` and restart `npm run dev`.

**CORS errors in the browser console**
You are calling the API directly rather than through the Vite proxy. Either
leave `VITE_API_BASE_URL=/api/v1`, or add your frontend origin to `CORS_ORIGINS`
in `backend/.env` and restart the backend.

**"Your session has expired" straight after signing in**
`JWT_SECRET_KEY` changed since the token was issued (for example, the backend
restarted with a new random key). Sign in again, and set a fixed key in `.env`.

**Sign-in is rejected but the password is right**
The account may be deactivated — an administrator can re-activate it on the
Users page. After three restarts of a seeded database, make sure you are using
the current credentials listed above.

**`npm install` fails or the build is odd**
Delete and reinstall: `rm -rf node_modules package-lock.json && npm install`.

**Port already in use**
`uvicorn app.main:app --port 8001`, or `npm run dev -- --port 5174`.

**The dashboard shows zeros**
That is correct for an empty farm — it will say so and offer to add your first
batch. Run `python -m app.db.seed` if you want demo data to look at.

---

## Security notes

- Passwords are hashed with bcrypt; plain text is never stored or returned
- JWT access tokens are short-lived and paired with refresh tokens
- Every endpoint checks the role — the interface hiding a button is a
  convenience, not the control
- All queries go through the ORM with bound parameters, so user input cannot
  reach SQL
- Validation runs on the server as well as in the browser; the browser check is
  only for a better experience
- Error responses are sanitised; full details go to the server log
- Secrets live in `.env`, which is git-ignored — only `.env.example` is committed
- With `APP_ENV=production`, the backend refuses to start if `JWT_SECRET_KEY`
  is still the default value

Before going live: set a strong `JWT_SECRET_KEY`, change every default password,
set `APP_ENV=production` and `DEBUG=false`, restrict `CORS_ORIGINS`, serve over
HTTPS, and back the database up regularly.
