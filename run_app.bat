@echo off
echo Starting Resume Optimizer...

:: Navigate to the directory where this script is located
cd /d "%~dp0"

:: Check for a virtual environment and activate it if present
IF EXIST venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) ELSE (
    echo Virtual environment (venv) not found. Running with system Python.
    echo Consider creating one with: python -m venv venv
)

:: Start the Flask application
echo Starting Flask server...
start "" http://127.0.0.1:5000/

:: Run the Python application.
:: The server will run in this window. Closing this window will stop the server.
python app.py

echo Flask server stopped.
pause
