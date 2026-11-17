@echo off
title MARK LVI - AI Assistant
cd /d "%~dp0"
echo ==============================================
echo   ⚡ Starting MARK LVI Personal AI Assistant
echo ==============================================

set "PYTHON_EXE=C:\Users\bisha\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Mark LVI exited with code %ERRORLEVEL%.
    pause
)
