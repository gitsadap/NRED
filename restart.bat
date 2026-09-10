@echo off
echo Killing stale Python processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "127.0.0.1:8000"') do (
    if not "%%a"=="0" taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak >nul
pm2 restart fastapi-backend
timeout /t 8 /nobreak >nul
echo Killing any new stale processes after restart...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "127.0.0.1:8000"') do (
    if not "%%a"=="0" taskkill /F /PID %%a 2>nul
)
echo Done.
pm2 status
