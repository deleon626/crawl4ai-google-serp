#!/bin/bash

# Crawl4AI Google SERP Parser - Launcher Script
# Runs both FastAPI backend and Streamlit frontend simultaneously

set -e

echo "🚀 Starting Crawl4AI Google SERP Parser..."
echo "=================================="

# Function to handle cleanup on script termination
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    # Kill all background jobs started by this script
    jobs -p | xargs -r kill
    wait
    echo "✅ All services stopped."
    exit 0
}

# Set trap to cleanup on script termination
trap cleanup SIGINT SIGTERM

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Please install UV first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if required files exist
if [[ ! -f "main.py" ]]; then
    echo "❌ main.py not found. Make sure you're in the project root directory."
    exit 1
fi

if [[ ! -f "frontend/streamlit_app.py" ]]; then
    echo "❌ frontend/streamlit_app.py not found. Make sure you're in the project root directory."
    exit 1
fi

echo "📦 Setting up environment..."

# Check if virtual environment exists, create if not
if [[ ! -d ".venv" ]]; then
    echo "   Creating virtual environment with UV..."
    uv venv
fi

# Install dependencies
echo "   Installing dependencies..."
if ! uv pip install -r requirements.txt --quiet; then
    echo "⚠️  Dependency conflict detected. Trying to resolve..."
    echo "   This might take a moment..."
    uv pip install -r requirements.txt --resolution=highest || {
        echo "❌ Failed to install dependencies. Please check requirements.txt"
        echo "   Try manually: uv pip install -r requirements.txt"
        exit 1
    }
fi

echo ""
echo "🔧 Starting FastAPI backend..."
echo "   Backend will be available at: http://localhost:8000"
echo "   API docs will be available at: http://localhost:8000/docs"

# Start FastAPI backend in background
uv run python main.py &
BACKEND_PID=$!

# Give backend time to start
sleep 3

echo ""
echo "🎨 Starting Streamlit frontend..."
echo "   Frontend will be available at: http://localhost:8501"

# Start Streamlit frontend in background
uv run streamlit run frontend/streamlit_app.py --server.headless true --server.runOnSave true &
FRONTEND_PID=$!

echo ""
echo "✅ Both services are starting up..."
echo "=================================="
echo "🌐 Multi-Platform Social Media Search:"
echo "   📱 Instagram: All, Reels, Posts, Accounts, TV, Locations (6 filters)"
echo "   💼 LinkedIn: All, Profiles, Companies, Posts, Jobs, Articles (6 filters)"
echo "   🔍 Query Preview: Real-time modified query display with Google URLs"
echo ""
echo "🌐 URLs:"
echo "   • Streamlit Frontend: http://localhost:8501"
echo "   • FastAPI Backend:    http://localhost:8000"
echo "   • API Documentation:  http://localhost:8000/docs"
echo ""
echo "💡 Press Ctrl+C to stop all services"
echo "=================================="

# Wait for background processes
wait