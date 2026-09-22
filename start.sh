#!/usr/bin/env bash
# ===========================================================================
#  E&J's CHICKENS — start the app on macOS and Linux
#
#  Run:  bash start.sh          (press Ctrl+C to stop both servers)
# ===========================================================================
set -euo pipefail
cd "$(dirname "$0")"

[ -d backend/.venv ]        || { echo " [X] Not set up yet. Run: bash setup.sh"; exit 1; }
[ -d frontend/node_modules ] || { echo " [X] Web packages missing. Run: bash setup.sh"; exit 1; }

echo
echo " Starting E&J's CHICKENS..."
echo " Press Ctrl+C to stop."
echo

( cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000 ) &
API_PID=$!
( cd frontend && npm run dev ) &
WEB_PID=$!

# One Ctrl+C stops both servers, not just the one in the foreground.
cleanup() { echo; echo " Stopping..."; kill "$API_PID" "$WEB_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

sleep 6
echo
echo " ==========================================================="
echo "  Open http://localhost:5173 in your browser"
echo "  Sign in with:  admin@ejchickens.com  /  Admin@12345"
echo " ==========================================================="
echo
wait
