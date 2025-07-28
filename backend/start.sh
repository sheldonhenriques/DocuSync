#!/bin/bash

# DocuSync Backend Startup Script

set -e

echo "Starting DocuSync Backend..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Please edit .env file with your configuration before running again."
        exit 1
    else
        echo "Error: Neither .env nor .env.example found!"
        exit 1
    fi
fi

# Load environment variables
if [ -f .env ]; then
    set -a  # automatically export all variables
    source .env
    set +a  # disable automatic export
fi

# Check required environment variables
required_vars=(
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY" 
    "SUPABASE_SERVICE_ROLE_KEY"
    "SECRET_KEY"
    "GITHUB_WEBHOOK_SECRET"
    "ORKES_API_KEY"
    "GOOGLE_API_KEY"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "Error: Missing required environment variables:"
    printf ' - %s\n' "${missing_vars[@]}"
    echo "Please set these variables in your .env file."
    exit 1
fi

# Check if we're in development mode
if [ "${DEBUG:-false}" = "true" ]; then
    echo "Running in development mode..."
    MODE="development"
else
    echo "Running in production mode..."
    MODE="production"
fi

# Install dependencies if requirements.txt has changed
if [ requirements.txt -nt venv/pyvenv.cfg ] 2>/dev/null || [ ! -d venv ]; then
    echo "Installing/updating dependencies..."
    if [ ! -d venv ]; then
        python -m venv venv
    fi
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Create logs directory
mkdir -p logs

# Run database migrations (if any)
echo "Checking database..."
# Add migration commands here when needed

# Start the application
echo "Starting FastAPI server..."

if [ "$MODE" = "development" ]; then
    # Development mode with auto-reload
    uvicorn main:app \
        --host 0.0.0.0 \
        --port ${PORT:-8000} \
        --reload \
        --log-level info \
        --access-log
else
    # Production mode
    uvicorn main:app \
        --host 0.0.0.0 \
        --port ${PORT:-8000} \
        --workers ${WORKERS:-4} \
        --log-level warning \
        --access-log \
        --log-config logging.json
fi