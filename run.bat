@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem ============================================================
rem  DSH Desktop Launcher - test runner
rem
rem  Usage:
rem    run.bat            launch with default port 3080
rem    run.bat 3090       launch on port 3090 (avoid conflict)
rem ============================================================

set "PORT=%~1"
if "%PORT%"=="" set "PORT=3080"
set "DSH_PORT=%PORT%"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] python not found in PATH. Install Python 3.10+ first.
    pause
    exit /b 1
)

echo ============================================
echo  DSH Desktop Launcher  (test)
echo  port : %PORT%
echo  url  : http://127.0.0.1:%PORT%
echo ============================================
echo.

python dsh_launcher.py
set "EC=%errorlevel%"

echo.
echo exit code: %EC%
echo.
pause
