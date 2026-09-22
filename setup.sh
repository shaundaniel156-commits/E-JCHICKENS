#!/usr/bin/env bash
# ===========================================================================
#  E&J's CHICKENS — one-time setup for macOS and Linux
#
#  Run:  bash setup.sh
#  Prepares the Python environment, the database, demo data and web packages.
#  Afterwards use start.sh to launch the app.
# ===========================================================================
set -euo pipefail
cd "$(dirname "$0")"

echo
echo " ==========================================================="
echo "  E&J's CHICKENS — setting up"
echo " ==========================================================="
echo

command -v python3 >/dev/null || { echo " [X] Python 3 not found. Install Python 3.11+ and try again."; exit 1; }
command -v node    >/dev/null || { echo " [X] Node.js not found. Install the LTS build from https://nodejs.org/ and try again."; exit 1; }
echo " [1/6] Found $(python3 --version)"
echo " [2/6] Found Node $(node --version)"

echo " [3/6] Creating the Python environment (this can take a minute)..."
[ -d backend/.venv ] || python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install --quiet --upgrade pip
backend/.venv/bin/python -m pip install --quiet -r backend/requirements.txt

# Reviewing the project uses SQLite, so MySQL does not need to be installed.
# To use MySQL instead, edit backend/.env and set DATABASE_URL — see the README.
if [ -f backend/.env ]; then
  echo " [4/6] backend/.env already exists — leaving your settings alone."
else
  echo " [4/6] Writing backend/.env with a freshly generated security key..."
  SECRET=$(backend/.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(64))")
  cat > backend/.env <<ENV
APP_ENV=development
DEBUG=true
DATABASE_URL=sqlite:///./ejchickens.db
JWT_SECRET_KEY=$SECRET
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
ENV
fi
[ -f frontend/.env ] || cp frontend/.env.example frontend/.env

echo " [5/6] Building the database and adding demo data..."
( cd backend && .venv/bin/python -m alembic upgrade head >/dev/null \
  && .venv/bin/python -m app.db.init_db \
  && .venv/bin/python -m app.db.seed )

echo " [6/6] Installing the web packages (this is the slowest step)..."
( cd frontend && npm install --no-fund --no-audit --loglevel=error )

echo
echo " ==========================================================="
echo "  Setup finished."
echo
echo "  Now run:  bash start.sh"
echo
echo "  Sign in with:  admin@ejchickens.com  /  Admin@12345"
echo " ==========================================================="
echo
