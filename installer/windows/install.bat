@echo off
setlocal EnableDelayedExpansion
title DarkMaxxer Windows Setup

echo ====================================================
echo        DARKMAXXER — Native Windows Setup
echo        Autonomous Local AI Workspace
echo ====================================================
echo.

where powershell >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
) else (
    echo [ERROR] PowerShell is required to run the automated installer.
    pause
)
