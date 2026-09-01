@echo off
setlocal

set "PORT=8765"
set "FOUND="

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    set "FOUND=1"
    echo Stopping wow-profile roster UI on port %PORT% ^(PID %%P^)...
    taskkill /PID %%P /F >nul
)

if not defined FOUND (
    echo No wow-profile roster UI server is listening on port %PORT%.
)

endlocal
