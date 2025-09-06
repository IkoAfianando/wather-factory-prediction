#!/bin/bash
# setup_environment.sh - Initialize Weather AI Profile environment

set -e

echo "Setting up Weather AI Profile environment..."

# Check prerequisites
echo "Checking prerequisites..."
command -v mongo >/dev/null 2>&1 || { echo "MongoDB client required but not installed. Aborting." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3 required but not installed. Aborting." >&2; exit 1; }

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found. Using .env.template defaults."
    cp .env.template .env
    echo "Please edit .env file with your actual configuration."
fi

# Test MongoDB connectivity
echo "Testing MongoDB connectivity..."
mongo --host ${APMS_MONGODB_HOST:-localhost:27017} --eval "db.runCommand('ping')" --quiet
if [ $? -eq 0 ]; then
    echo "✅ MongoDB connection successful"
else
    echo "❌ MongoDB connection failed. Check APMS_MONGODB_HOST in .env"
    exit 1
fi

# Create MongoDB collections and indexes
echo "Setting up MongoDB collections..."
mongo ${APMS_MONGODB_HOST:-localhost:27017}/${APMS_DB_WEATHER_AI:-apms_weather_ai} < 50_implementation/deployment/mongodb_setup.js

# Test weather API (placeholder)
echo "Testing weather API connectivity..."
if [ -n "${WEATHER_API_KEY}" ] && [ "${WEATHER_API_KEY}" != "your_openweather_api_key_here" ]; then
    # PLACEHOLDER: Add actual weather API test
    echo "⚡ Weather API test - PLACEHOLDER implementation needed"
else
    echo "⚡ Weather API key not configured - PLACEHOLDER integration"
fi

# Install Python dependencies (if requirements exist)
if [ -f requirements.txt ]; then
    echo "Installing Python dependencies..."
    pip3 install -r requirements.txt
else
    echo "ℹ️ No requirements.txt found - manual dependency management required"
fi

echo "✅ Environment setup complete!"
echo "Next steps:"
echo "1. Edit .env file with your actual API keys and configurations"
echo "2. Run ./scripts/run_backfill.sh to process historical data" 
echo "3. Follow SOP in 40_sop/SOP_weather_profile.md"