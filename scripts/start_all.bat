@echo off
setlocal EnableExtensions EnableDelayedExpansion
rem Startup script for DVG Invoice Approval System on Windows
rem Entspricht start_all.sh fuer macOS

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"

set "COMPOSE_PROJECT_NAME=dvg-app"

echo ===========================================
echo   DVG Invoice System - Startup (Windows)
echo ===========================================
echo.

rem 0. Python-Befehl ermitteln
set "PYTHON_CMD="
where python3 >nul 2>nul && set "PYTHON_CMD=python3" && goto :py_ok
where python >nul 2>nul && set "PYTHON_CMD=python" && goto :py_ok
where py >nul 2>nul && set "PYTHON_CMD=py" && goto :py_ok
echo [FEHLER] Kein Python gefunden! Bitte installiere Python 3.
pause
exit /b 1
:py_ok
echo [INFO] Python-Befehl: %PYTHON_CMD%

rem 1. Docker pruefen und starten
echo.
echo ^>^>^> 1. Starte Docker-Compose-Infrastruktur...
where docker >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo [FEHLER] Docker ist nicht installiert oder nicht im PATH!
  pause
  exit /b 1
)
docker info >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo [FEHLER] Docker Desktop laeuft nicht!
  echo    Bitte starte Docker Desktop und warte, bis es bereit ist.
  pause
  exit /b 1
)

docker compose up -d
if %ERRORLEVEL% neq 0 (
  echo    [WARNUNG] Erster Start hatte Fehler, versuche force-recreate...
  docker compose up -d --force-recreate
)
echo    [OK] Docker-Container gestartet.

rem 2. Warte auf Zeebe Gateway
echo.
echo ^>^>^> 2. Warte auf Zeebe Gateway...
set "ZEEBE_READY=0"
for /L %%i in (1,1,60) do (
  if !ZEEBE_READY! equ 0 (
    curl -sf http://localhost:9600/actuator/health >nul 2>nul
    if !ERRORLEVEL! equ 0 (
      set "ZEEBE_READY=1"
      echo    [OK] Zeebe ist bereit.
    ) else (
      echo    Warte auf Zeebe... (%%i/60^)
      timeout /t 2 /nobreak >nul
    )
  )
)
if %ZEEBE_READY% equ 0 (
  echo    [FEHLER] Zeebe ist nach 120s nicht erreichbar!
  echo    Pruefe: docker compose logs zeebe
  pause
  exit /b 1
)

rem 3. Deploy BPMN and Forms
echo.
echo ^>^>^> 3. Stelle BPMN-Prozess und Formulare bereit...
%PYTHON_CMD% "%SCRIPT_DIR%deploy_bmpn.py"
if %ERRORLEVEL% neq 0 (
  echo    [FEHLER] BPMN-Deployment fehlgeschlagen!
  pause
  exit /b 1
)

rem 4. Starte Dienste in eigenen CMD-Fenstern
echo.
echo ^>^>^> 4. Starte Backend-Dienste in neuen Fenstern...

echo    -^> Starte gRPC Server...
start "gRPC-Server" cmd /k "cd /d ""%PROJECT_ROOT%"" && echo === gRPC-Server === && %PYTHON_CMD% grpc-service\src\server.py"

echo    -^> Starte Worker...
start "Worker" cmd /k "cd /d ""%PROJECT_ROOT%"" && echo === Worker === && %PYTHON_CMD% worker\src\worker.py"

echo    -^> Starte RabbitMQ Consumer...
start "RabbitMQ-Consumer" cmd /k "cd /d ""%PROJECT_ROOT%"" && echo === RabbitMQ Consumer === && %PYTHON_CMD% zahlungssystem\src\consumer.py"

echo.
echo ===========================================================
echo   [ERFOLG] Alle Systemkomponenten wurden gestartet!
echo ===========================================================
echo   - Tasklist: http://localhost:8082  (Login: demo / demo)
echo   - Operate:  http://localhost:8081  (Login: demo / demo)
echo   - RabbitMQ: http://localhost:15672 (Login: admin / admin)
echo.
echo   Du kannst jetzt eine neue E-Mail-Rechnung simulieren mit:
echo   -^> %PYTHON_CMD% scripts\auto_email_start.py
echo ===========================================================
echo.
pause
