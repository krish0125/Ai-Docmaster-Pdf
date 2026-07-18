@echo off
echo ==========================================
echo Starting AI DocMaster Services
echo ==========================================

:: Start Flask Backend Server in a new window
echo Starting Backend Server on http://localhost:5001...
start "AI DocMaster Backend" cmd /k "cd backend && ..\venv\Scripts\python.exe app.py"

:: Start Frontend Server in a new window
echo Starting Frontend Server on http://localhost:5500...
start "AI DocMaster Frontend" cmd /k "cd frontend && ..\venv\Scripts\python.exe serve.py"

echo.
echo Both servers have been launched in separate terminal windows!
echo - Frontend: http://localhost:5500
echo - Backend:  http://localhost:5001
echo ==========================================
