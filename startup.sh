#!/usr/bin/env bash
# Azure App Service Linux Custom Startup Script
set -e

echo "Starting Intelligent Knowledge Hub on Azure App Service..."

# Install or sync dependencies if running in code-deploy mode
if [ -f "requirements.txt" ]; then
    echo "Verifying Python dependencies..."
    pip install --no-cache-dir -r requirements.txt
fi

# Run Uvicorn production server
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-2}
