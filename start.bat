@echo off
echo ==================================================
echo   Starting AI DocMaster (Backend ^& Frontend)
echo ==================================================
echo.

:: Start the Backend in a new terminal window
echo Starting Backend...
start "AI DocMaster - Backend" cmd /k "venv\Scripts\activate && python backend\app.py"

:: Start the Frontend in a new terminal window
echo Starting Frontend...
start "AI DocMaster - Frontend" cmd /k "venv\Scripts\activate && python frontend\serve.py"

echo.
echo Both servers are starting up!
echo You can access the app at: http://127.0.0.1:5500
echo ==================================================
