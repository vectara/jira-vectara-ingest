@echo off
REM Setup script for jira-vectara-ingest (Windows)

echo Setting up jira-vectara-ingest...
echo.

REM Check Python
echo Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python 3.8+
    exit /b 1
)
python --version

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Failed to create virtual environment
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies (this takes ~5 seconds)...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies
    exit /b 1
)

REM Copy config if needed
if not exist config.yaml (
    echo Creating config.yaml from sample...
    copy config.sample.yaml config.yaml
    echo.
    echo Please edit config.yaml with your credentials:
    echo   - vectara.api_key
    echo   - vectara.corpus_key
    echo   - jira.base_url
    echo   - jira.username
    echo   - jira.api_token
    echo   - jira.jql
) else (
    echo config.yaml already exists
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo   1. Edit config.yaml with your credentials
echo   2. Run: venv\Scripts\activate
echo   3. Run: python jira_ingest.py --config config.yaml
echo.

pause
