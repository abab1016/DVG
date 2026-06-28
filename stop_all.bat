@echo off
rem Stop script for DVG Invoice Approval System on Windows
rem Entspricht stop_all.sh fuer macOS

set "COMPOSE_PROJECT_NAME=dvg-app"

echo ===========================================
echo   DVG Invoice System - Stop (Windows)
echo ===========================================
echo.

rem 1. Python-Dienste stoppen
echo ^>^>^> 1. Stoppe Python-Dienste...
set "STOPPED=0"

tasklist /FI "WINDOWTITLE eq gRPC-Server*" 2>nul | find "cmd.exe" >nul
if %ERRORLEVEL% equ 0 (
  taskkill /FI "WINDOWTITLE eq gRPC-Server*" /F >nul 2>nul
  echo    [OK] gRPC-Server gestoppt.
  set /a STOPPED+=1
) else (
  echo    [-] gRPC-Server laeuft nicht.
)

tasklist /FI "WINDOWTITLE eq Worker*" 2>nul | find "cmd.exe" >nul
if %ERRORLEVEL% equ 0 (
  taskkill /FI "WINDOWTITLE eq Worker*" /F >nul 2>nul
  echo    [OK] Worker gestoppt.
  set /a STOPPED+=1
) else (
  echo    [-] Worker laeuft nicht.
)

tasklist /FI "WINDOWTITLE eq RabbitMQ-Consumer*" 2>nul | find "cmd.exe" >nul
if %ERRORLEVEL% equ 0 (
  taskkill /FI "WINDOWTITLE eq RabbitMQ-Consumer*" /F >nul 2>nul
  echo    [OK] RabbitMQ Consumer gestoppt.
  set /a STOPPED+=1
) else (
  echo    [-] RabbitMQ Consumer laeuft nicht.
)

echo.
echo    %STOPPED% Dienst(e) gestoppt.

rem 2. Docker-Container stoppen
echo.
echo ^>^>^> 2. Stoppe Docker-Container...
docker compose down --remove-orphans 2>nul
echo    [OK] Docker-Container gestoppt.

echo.
echo ===========================================
echo   [ERFOLG] Alles wurde gestoppt!
echo ===========================================
echo   Zum Neustarten: start_all.bat
echo ===========================================
echo.
pause
