@echo off
REM Setup script for AI Legal Analyzer

echo.
echo ====================================
echo AI Legal Analyzer - Full Setup
echo ====================================
echo.

REM Step 1: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Step 2: Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    pause
    exit /b 1
)

echo ✓ Python and Node.js found
echo.

REM Step 3: Install Python dependencies
echo Installing backend dependencies...
cd backend
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies
    pause
    exit /b 1
)
echo ✓ Backend dependencies installed
echo.
cd ..

REM Step 4: Install frontend dependencies
echo Installing frontend dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies
    pause
    exit /b 1
)
echo ✓ Frontend dependencies installed
echo.
cd ..

echo.
echo ====================================
echo Setup Complete!
echo ====================================
echo.
echo NEXT STEPS:
echo 1. Update backend\.env with your credentials:
echo    - MYSQL_USER and MYSQL_PASSWORD
echo    - GEMINI_API_KEY (get from https://aistudio.google.com/app/apikeys)
echo.
echo 2. Run migrations (in MySQL):
echo    - Open migrations folder
echo    - Run SQL files in order: 001, 002, 003
echo.
echo 3. To start the project:
echo    - Run: npm run dev (in project root)
echo.
pause
