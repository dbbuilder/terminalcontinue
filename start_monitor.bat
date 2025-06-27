@echo off
REM Terminal Continue Monitor - Windows Batch Startup Script
REM 
REM This script provides an easy way to start the Terminal Continue Monitor
REM application on Windows systems.

echo =================================================
echo Terminal Continue Monitor v1.0.0
echo Automated Terminal Session Activity Monitor
echo =================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/
    echo.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if dependencies are installed
echo Checking dependencies...
pip show pywinauto >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Check if configuration file exists
if not exist "config.yaml" (
    echo Configuration file not found. Copying from example...
    copy config.example.yaml config.yaml
    echo.
    echo IMPORTANT: Please review and modify config.yaml as needed
    echo Press any key to continue or Ctrl+C to exit and configure first
    pause
)

REM Start the application
echo.
echo Starting Terminal Continue Monitor...
echo Press Ctrl+C to stop monitoring
echo.
python src\terminal_monitor.py

REM Deactivate virtual environment
deactivate

echo.
echo Terminal Continue Monitor stopped.
pause
