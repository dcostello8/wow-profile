@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo Starting wow-profile roster UI...
echo.
"%PYTHON_EXE%" wow_profile.py roster-ui

endlocal
