@echo off
echo Resume Optimizer Debug Script
echo -----------------------------
echo.
echo Current directory before CD: %CD%
pause

echo Changing directory to script location: %~dp0
cd /d "%~dp0"
echo Current directory after CD: %CD%
pause

IF EXIST venv\Scripts\activate.bat (
    echo Virtual environment (venv) found. Attempting to activate...
    call venv\Scripts\activate.bat
    echo Virtual environment activation attempted. Check for errors above.
) ELSE (
    echo Virtual environment (venv) not found in %CD%\venv
    echo Will attempt to use system Python. Ensure Python is in your PATH.
    echo To create a venv: python -m venv venv
)
pause

echo Attempting to launch web browser for http://127.0.0.1:5000/
start "" http://127.0.0.1:5000/
echo Web browser launch command executed.
pause

echo Now attempting to run the Flask application with: python app.py
echo If Python or app.py is not found, or if app.py crashes, errors should appear below.
python app.py

echo ---------------------------------------------------------------------
echo Flask server (python app.py) has stopped or failed to start.
echo If the server started, you would have seen Flask's output above,
echo and this message would only appear after you stop the server (e.g., CTRL+C).
echo If it closed instantly, check for error messages above this section.
echo ---------------------------------------------------------------------
pause
