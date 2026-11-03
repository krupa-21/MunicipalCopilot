@echo off
echo ======================================================================
echo   AHMEDABAD MUNICIPAL CORPORATION (AMC) - KNOWLEDGE COPILOT
echo   Seva First Innovation Challenge 2026 (SSIP 2.0)
echo ======================================================================
echo.

set SCRIPT_DIR=%~dp0

echo [1/3] Starting FastAPI Backend on port 8000...
start "AMC Copilot - Backend (Port 8000)" cmd /k "cd /d %SCRIPT_DIR%backend && set OLLAMA_KEEP_ALIVE=30m && .\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo [2/3] Starting React Frontend on port 5173...
start "AMC Copilot - Frontend (Port 5173)" cmd /k "cd /d %SCRIPT_DIR%frontend && npm run dev"

echo [3/3] Waiting for services to initialize...
timeout /t 4 /nobreak >nul

echo Opening AMC Municipal Knowledge Copilot in your browser...
start http://localhost:5173

echo.
echo ======================================================================
echo   Both services are running!
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000/docs (Swagger UI)
echo ======================================================================
pause