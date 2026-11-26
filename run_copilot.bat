@echo off
echo ======================================================================
echo   AHMEDABAD MUNICIPAL CORPORATION (AMC) - KNOWLEDGE COPILOT
echo   Seva First Innovation Challenge 2026 (SSIP 2.0)
echo ======================================================================
echo.

set SCRIPT_DIR=%~dp0

echo [1/4] Checking Ollama Server on port 11434...
netstat -ano | findstr ":11434" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo Starting Ollama Server...
    start "AMC Copilot - Ollama (Port 11434)" cmd /k "ollama serve"
    timeout /t 3 /nobreak >nul
) else (
    echo Ollama is already running on port 11434.
)

echo [2/4] Starting FastAPI Backend on port 8000...
set "PYTHON_EXE=%SCRIPT_DIR%backend\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe"
start "AMC Copilot - Backend (Port 8000)" cmd /k "cd /d %SCRIPT_DIR%backend && set OLLAMA_KEEP_ALIVE=30m && %PYTHON_EXE% -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo [3/4] Starting React Frontend on port 5173...
start "AMC Copilot - Frontend (Port 5173)" cmd /k "cd /d %SCRIPT_DIR%frontend && npm run dev"

echo [4/4] Waiting for services to initialize...
timeout /t 4 /nobreak >nul

echo Opening AMC Municipal Knowledge Copilot in your browser...
start http://localhost:5173

echo.
echo ======================================================================
echo   All services are running!
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000/docs (Swagger UI)
echo   Ollama   : http://127.0.0.1:11434
echo ======================================================================
pause