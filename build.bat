@echo off
rem ============================================================
rem  DeepSeek Harness Desktop - one-click build script
rem  Usage : double-click this file (or run: build.bat)
rem  Output: dist\DeepSeekHarness.exe
rem ============================================================
setlocal
cd /d "%~dp0"

title DeepSeek Harness Desktop - Build

echo ============================================
echo   DeepSeek Harness Desktop - one-click build
echo ============================================
echo.

rem ---- 1. check Python ----
set "PY=python"
where python >nul 2>nul
if errorlevel 1 set "PY=py -3"
%PY% --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ and check "Add to PATH".
    goto :fail
)
for /f "delims=" %%v in ('%PY% --version 2^>^&1') do set "PYVER=%%v"
echo [1/4] Python found: %PYVER%

rem ---- 2. check / install build dependencies ----
%PY% -c "import PyInstaller, webview" >nul 2>nul
if errorlevel 1 (
    echo [2/4] Installing build dependencies from requirements.txt ...
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 goto :fail
) else (
    echo [2/4] Build dependencies ready
)

rem ---- 3. check whether DeepSeekHarness.exe is locked ----
tasklist /FI "IMAGENAME eq DeepSeekHarness.exe" 2>nul | find /I "DeepSeekHarness.exe" >nul
if not errorlevel 1 goto :app_running
goto :do_build

:app_running
echo [3/4] DeepSeekHarness.exe is currently RUNNING.
echo        A running instance locks dist\DeepSeekHarness.exe and the build will fail.
set /p CLOSE_APP="        Close it now automatically? (Y/N): "
if /I "%CLOSE_APP%"=="Y" (
    taskkill /F /T /IM DeepSeekHarness.exe >nul 2>nul
    timeout /t 2 /nobreak >nul
) else (
    echo.
    echo [HINT] Please quit the desktop app first, then run this script again.
    goto :fail
)

:do_build
echo [3/4] Building with PyInstaller (usually 1-3 minutes, please wait) ...
echo.
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name DeepSeekHarness --icon icon.ico --collect-all webview dsh_launcher.py
if errorlevel 1 goto :fail

rem ---- 4. verify output ----
if not exist "dist\DeepSeekHarness.exe" (
    echo [ERROR] dist\DeepSeekHarness.exe not found. Build may have failed.
    goto :fail
)
echo.
echo ============================================
echo   [4/4] BUILD OK: dist\DeepSeekHarness.exe
echo   You can now run the new desktop app.
echo ============================================
pause
exit /b 0

:fail
echo.
echo [FAILED] Build did not complete. Check the errors above.
pause
exit /b 1
