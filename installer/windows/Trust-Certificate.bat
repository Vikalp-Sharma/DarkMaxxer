@echo off
:: [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
:: Windows Smart App Control & SmartScreen Certificate Trust Utility
title DarkMaxxer Certificate Trust Tool

echo ====================================================
echo   Trusting DarkMaxxer Authenticode Certificate
echo   Bypassing Windows SmartScreen & Smart App Control
echo ====================================================
echo.

net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ELEVATING TO ADMINISTRATOR]
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

if exist "%~dp0DarkMaxxer.cer" (
    set CERT_PATH=%~dp0DarkMaxxer.cer
) else if exist "%~dp0certs\DarkMaxxer.cer" (
    set CERT_PATH=%~dp0certs\DarkMaxxer.cer
) else (
    echo [ERROR] DarkMaxxer.cer not found!
    pause
    exit /b 1
)

echo Installing certificate into Trusted Root Certification Authorities...
certutil -addstore -f "ROOT" "%CERT_PATH%"

echo Installing certificate into Trusted Publishers store...
certutil -addstore -f "TrustedPublisher" "%CERT_PATH%"

echo.
echo ====================================================
echo [SUCCESS] DarkMaxxer is now a Trusted Publisher!
echo Windows Smart App Control & SmartScreen will allow
echo DarkMaxxer without any security warnings.
echo ====================================================
pause
