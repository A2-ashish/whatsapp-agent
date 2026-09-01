@echo off
echo Starting WhatsApp Commerce Platform...

echo.
echo [1/3] Building and starting backend services via Docker...
docker compose up -d --build

echo.
echo [2/3] Waiting for database to initialize and seeding data...
timeout /t 5 /nobreak >nul
docker compose exec backend uv run python -m app.seed

echo.
echo [3/3] Starting the React Dashboard...
cd dashboard
call npm install
echo Dashboard starting... (Press CTRL+C to stop)
npm run dev
