@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "PYTHON=%PROJECT_ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Python virtual environment not found at %PYTHON%
    exit /b 1
)

"%PYTHON%" -m pip install pyinstaller
if errorlevel 1 exit /b 1

pushd "%PROJECT_ROOT%"
if exist "dist\WowProfile.exe" del /q "dist\WowProfile.exe"
"%PYTHON%" -m PyInstaller --clean --noconfirm WowProfile.spec
set "RESULT=%ERRORLEVEL%"
popd

if not "%RESULT%" == "0" exit /b %RESULT%
echo Built dist\WowProfile\WowProfile.exe