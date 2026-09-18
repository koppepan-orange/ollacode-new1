@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

set "ROOT=%~dp0"

REM Prefer venv python
if exist "%ROOT%.venv\Scripts\python.exe" (
    set "PYTHON=%ROOT%.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        set "PYTHON=python"
    ) else (
        where py >nul 2>&1
        if !ERRORLEVEL! equ 0 (
            set "PYTHON=py"
        ) else (
            echo [ERROR] Python not found.
            exit /b 1
        )
    )
)

"%PYTHON%" "%ROOT%main.py" %*
