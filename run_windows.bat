@echo off
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.9 or newer from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo Installing/updating dependencies...
pip install -r requirements.txt --quiet
echo Starting the application...
python run.py
pause
