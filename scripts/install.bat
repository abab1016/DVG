@echo off
rem Installation and setup script for DVG Invoice Approval System on Windows

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"

echo ==========================================================
echo   DVG Invoice System - Installation ^& Setup (Windows)
echo ==========================================================
echo.

rem 1. Plattform aus plattform.txt auslesen
set "PLATFORM=windows"
if exist plattform.txt (
  set /p PLATFORM=<plattform.txt
  echo [INFO] Plattform aus plattform.txt erkannt: %PLATFORM%
) else (
  echo [INFO] plattform.txt nicht gefunden. Verwende Standard: windows
)

rem 2. Ordner vorbereiten
echo.
echo ^>^>^> [1/4] Bereite Arbeitsordner vor...
if not exist Rechnungsdaten (
  mkdir Rechnungsdaten
  echo     -^> Ordner 'Rechnungsdaten' erstellt.
) else (
  echo     -^> Ordner 'Rechnungsdaten' verifiziert.
)

rem 3. Python suchen
echo.
echo ^>^>^> [2/4] Ueberpruefe Python-Installation...
set "PYTHON_CMD="

where python3 >nul 2>nul
if %ERRORLEVEL% equ 0 (
  set "PYTHON_CMD=python3"
  goto :python_found
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
  set "PYTHON_CMD=python"
  goto :python_found
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
  set "PYTHON_CMD=py"
  goto :python_found
)

echo [FEHLER] Kein Python installiert! Bitte installiere Python 3 und setze den Haken bei 'Add python.exe to PATH'.
pause
exit /b 1

:python_found
echo     -^> Verwende Python-Befehl: %PYTHON_CMD%
%PYTHON_CMD% --version

rem 4. Abhängigkeiten installieren
echo.
echo ^>^>^> [3/4] Installiere Python-Abhaengigkeiten...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r worker\requirements.txt
%PYTHON_CMD% -m pip install -r grpc-service\requirements.txt
%PYTHON_CMD% -m pip install -r zahlungssystem\requirements.txt

if %ERRORLEVEL% equ 0 (
  echo     [OK] Python-Abhaengigkeiten erfolgreich installiert.
) else (
  echo     [WARNUNG] Installation der Python-Abhaengigkeiten fehlgeschlagen oder unvollstaendig.
)

rem 5. Docker-Images vorbereiten
echo.
echo ^>^>^> [4/4] Bereite Docker-Infrastruktur vor...
where docker >nul 2>nul
if %ERRORLEVEL% equ 0 (
  docker info >nul 2>nul
  if %ERRORLEVEL% equ 0 (
    echo     -^> Docker-Daemon laeuft. Lade Container-Images herunter...
    docker compose pull
    echo     [OK] Docker-Images heruntergeladen.
  ) else (
    echo     [INFO] Docker laeuft gerade nicht oder ist nicht gestartet.
    echo            Die Images werden beim Starten der Container geladen.
  )
) else (
  echo     [INFO] Docker ist nicht installiert.
)

echo.
echo ==========================================================
echo   [ERFOLG] Installation und Setup abgeschlossen!
echo ==========================================================
echo   Die Plattform wurde auf '%PLATFORM%' konfiguriert.
echo   Du kannst das System nun starten mit:
echo   -^> scripts\start_all.bat
echo ==========================================================
echo.
pause
