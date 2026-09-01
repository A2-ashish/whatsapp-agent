#!/bin/bash
echo "Starting WhatsApp Commerce Platform..."

echo -e "\n[1/3] Building and starting backend services via Docker..."
docker compose up -d --build

echo -e "\n[2/3] Waiting for database to initialize and seeding data..."
sleep 5
docker compose exec backend uv run python -m app.seed

echo -e "\n[3/3] Starting the React Dashboard..."
cd dashboard || exit
npm install
echo "Dashboard starting... (Press CTRL+C to stop)"
npm run dev
