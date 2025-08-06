@echo off
REM Crawl4AI Google SERP Parser - Windows Launcher Script
REM Runs both FastAPI backend and Streamlit frontend simultaneously

echo 🚀 Starting Crawl4AI Google SERP Parser...
echo ==================================

REM Check if UV is installed
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ UV is not installed. Please install UV first:
    echo    powershell -c "irm https://astral.sh/uv/install.sh | iex"
    pause
    exit /b 1
)

REM Check if required files exist
if not exist "main.py" (
    echo ❌ main.py not found. Make sure you're in the project root directory.
    pause
    exit /b 1
)

if not exist "frontend\streamlit_app.py" (
    echo ❌ frontend\streamlit_app.py not found. Make sure you're in the project root directory.
    pause
    exit /b 1
)

echo 📦 Installing/checking dependencies...
uv pip install -r requirements.txt --quiet

echo.
echo 🔧 Starting FastAPI backend...
echo    Backend will be available at: http://localhost:8000
echo    API docs will be available at: http://localhost:8000/docs

REM Start FastAPI backend in background
start /b "FastAPI Backend" uv run python main.py

REM Give backend time to start
timeout /t 3 /nobreak >nul

echo.
echo 🎨 Starting Streamlit frontend...
echo    Frontend will be available at: http://localhost:8501

echo.
echo ✅ Both services are starting up...
echo ==================================
echo 📱 Instagram Content Filtering Available:
echo    🌍 All Content  🎬 Reels Only  📷 Posts Only  👤 Accounts Only
echo.
echo 🌐 URLs:
echo    • Streamlit Frontend: http://localhost:8501
echo    • FastAPI Backend:    http://localhost:8000
echo    • API Documentation:  http://localhost:8000/docs
echo.
echo 💡 Press Ctrl+C to stop all services
echo ==================================

REM Start Streamlit frontend (this will block)
uv run streamlit run frontend\streamlit_app.py --server.headless true --server.runOnSave true