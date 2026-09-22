@echo off
REM ===========================================================================
REM  E&J's CHICKENS - start the app on Windows
REM
REM  Double-click this file. It opens the backend and the web app in their own
REM  windows, then opens your browser. Run setup.bat first if you have not.
REM
REM  To stop the app, close the two windows this opens.
REM ===========================================================================
setlocal
cd /d "%~dp0"

if not exist "backend\.venv" (
  echo.
  echo  [X] The project is not set up yet.
  echo      Double-click  setup.bat  first, then run this again.
  echo.
  pause
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo.
  echo  [X] The web packages are missing.
  echo      Double-click  setup.bat  first, then run this again.
  echo.
  pause
  exit /b 1
)

echo.
echo  Starting E^&J's CHICKENS...
echo.
echo  Two windows will open - leave them running. Close them to stop the app.
echo.

start "E&J's CHICKENS - server" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
timeout /t 5 /nobreak >nul
start "E&J's CHICKENS - web app" cmd /k "cd /d "%~dp0frontend" && npm run dev"
timeout /t 6 /nobreak >nul
start "" http://localhost:5173

echo  The app should now be opening at http://localhost:5173
echo.
echo  Sign in with:  admin@ejchickens.com  /  Admin@12345
echo.
pause
