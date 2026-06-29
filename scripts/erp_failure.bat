@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "COMPONENT=erp"
goto :find_python

:find_python
where python3 >nul 2>nul && set "PYTHON_CMD=python3" && goto :run
where python >nul 2>nul && set "PYTHON_CMD=python" && goto :run
where py >nul 2>nul && set "PYTHON_CMD=py -3" && goto :run
echo [FEHLER] Kein Python 3 gefunden.
exit /b 1

:run
%PYTHON_CMD% "%SCRIPT_DIR%component_failure.py" "%COMPONENT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
if "%~1"=="" pause
exit /b %EXIT_CODE%
