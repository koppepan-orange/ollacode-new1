@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

echo ==========================================
echo   OllaCode Setup - Local AI Agent CLI
echo ==========================================
echo.

REM Work from this script's directory, not the caller's current directory
cd /d "%~dp0"

REM Check Python.
REM Prefer the Python Launcher because Windows may have a Microsoft Store
REM python.exe alias on PATH that exists but is not an actual interpreter.
set "PYTHON="

where py >nul 2>&1
if !ERRORLEVEL! equ 0 (
    py -3.10 --version >nul 2>&1
    if !ERRORLEVEL! equ 0 set "PYTHON=py -3.10"
)

if not defined PYTHON (
    where py >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        py --version >nul 2>&1
        if !ERRORLEVEL! neq 0 set "PYTHON="
        if !ERRORLEVEL! equ 0 set "PYTHON=py"
    )
)

if not defined PYTHON (
    where python >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        python --version >nul 2>&1
        if !ERRORLEVEL! equ 0 set "PYTHON=python"
    )
)

if not defined PYTHON (
    echo [ERROR] Python 3.10+ was not found or could not be executed.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo [OK] Python found: !PYTHON!
%PYTHON% --version
if !ERRORLEVEL! neq 0 (
    echo [ERROR] Python was found but could not be executed.
    pause
    exit /b 1
)
echo.

REM Create virtual environment
if exist ".venv\Scripts\python.exe" (
    echo [OK] Virtual environment already exists.
) else (
    echo Creating virtual environment...
    %PYTHON% -m venv .venv
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

echo.
echo Installing dependencies...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if !ERRORLEVEL! neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [OPTIONAL] Installing Playwright browser...
.venv\Scripts\python.exe -m playwright install chromium
if !ERRORLEVEL! neq 0 (
    echo [WARN] Playwright install skipped. Browser control will not be available.
)

echo.
echo ==========================================
echo   Setup complete!
echo   Run: ollacode.bat   to start OllaCode
echo ==========================================
echo.
pause
