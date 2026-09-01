@echo off
echo Stopping WhatsApp Commerce Platform...

echo [1/2] Stopping Docker containers...
docker compose down

echo [2/2] Stopping React Dashboard...
taskkill /F /IM node.exe >nul 2>&1

echo Platform stopped successfully!
timeout /t 3 >nul
