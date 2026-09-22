@echo off
REM ===========================================================================
REM  E&J's CHICKENS - one-time setup for Windows
REM
REM  Double-click this file. It prepares everything the app needs:
REM  a Python environment, the database, demo data, and the web packages.
REM  Run it once. Afterwards, use start.bat to launch the app.
REM ===========================================================================
setlocal
cd /d "%~dp0"

echo.
echo  ===========================================================
echo   E^&J's CHICKENS - setting up
echo  ===========================================================
echo.

REM --- check Python ----------------------------------------------------------
where py >nul 2>nul
if %errorlevel%==0 (set "PY=py") else (set "PY=python")
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo  [X] Python was not found.
  echo.
  echo      Install Python 3.11 or newer from https://www.python.org/downloads/
  echo      IMPORTANT: tick "Add python.exe to PATH" on the first screen.
  echo      Then run this file again.
  echo.
  pause
  exit /b 1
)
for /f "tokens=*" %%v in ('%PY% --version') do echo  [1/6] Found %%v

REM --- check Node ------------------------------------------------------------
node --version >nul 2>nul
if errorlevel 1 (
  echo  [X] Node.js was not found.
  echo.
  echo      Install the LTS version from https://nodejs.org/
  echo      Then run this file again.
  echo.
  pause
  exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do echo  [2/6] Found Node %%v

REM --- Python environment ----------------------------------------------------
echo  [3/6] Creating the Python environment (this can take a minute)...
if not exist "backend\.venv" (
  %PY% -m venv backend\.venv
  if errorlevel 1 (
    echo  [X] Could not create the Python environment.
    pause
    exit /b 1
  )
)
call backend\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
call backend\.venv\Scripts\python.exe -m pip install --quiet -r backend\requirements.txt
if errorlevel 1 (
  echo  [X] Installing the Python packages failed. Check your internet connection.
  pause
  exit /b 1
)

REM --- configuration ---------------------------------------------------------
REM Reviewing the project uses SQLite, so MySQL does not need to be installed.
REM To use MySQL instead, edit backend\.env and set DATABASE_URL - see the README.
if exist "backend\.env" (
  echo  [4/6] backend\.env already exists - leaving your settings alone.
) else (
  echo  [4/6] Writing backend\.env with a freshly generated security key...
  call backend\.venv\Scripts\python.exe -c "import secrets, pathlib; pathlib.Path('backend/.env').write_text('APP_ENV=development\nDEBUG=true\nDATABASE_URL=sqlite:///./ejchickens.db\nJWT_SECRET_KEY=' + secrets.token_urlsafe(64) + '\nCORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173\n', encoding='utf-8')"
)
if not exist "frontend\.env" copy /y "frontend\.env.example" "frontend\.env" >nul

REM --- database --------------------------------------------------------------
echo  [5/6] Building the database and adding demo data...
pushd backend
call .venv\Scripts\python.exe -m alembic upgrade head
if errorlevel 1 (
  echo  [X] Creating the database tables failed.
  popd
  pause
  exit /b 1
)
call .venv\Scripts\python.exe -m app.db.init_db
call .venv\Scripts\python.exe -m app.db.seed
popd

REM --- frontend packages -----------------------------------------------------
echo  [6/6] Installing the web packages (this is the slowest step)...
pushd frontend
call npm install --no-fund --no-audit --loglevel=error
if errorlevel 1 (
  echo  [X] npm install failed. Check your internet connection.
  popd
  pause
  exit /b 1
)
popd

echo.
echo  ===========================================================
echo   Setup finished.
echo.
echo   Now double-click  start.bat  to open the app.
echo.
echo   Sign in with:  admin@ejchickens.com  /  Admin@12345
echo  ===========================================================
echo.
pause
