@echo off
setlocal
cd /d "%~dp0"

echo ======================================================
echo           DevPilot - Development Workspace Manager
echo ======================================================

:: Check python executable
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found on your system PATH!
    echo Please install Python 3.10+ and ensure it is added to PATH.
    pause
    exit /b 1
)

:: Run DevPilot
python main.py %*

if %ERRORLEVEL% neq 0 (
    echo [ERROR] DevPilot exited with code %ERRORLEVEL%
    pause
)
