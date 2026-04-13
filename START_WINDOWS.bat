@echo off
echo.
echo  ============================================
echo   Pre-Demolition Audit Generator - Lawmens
echo  ============================================
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

:: Install requirements
echo Installing required packages (first run only)...
python -m pip install flask weasyprint matplotlib anthropic Pillow python-dotenv -q
if errorlevel 1 (
    echo WARNING: Some packages may not have installed correctly.
)

echo.
echo  Starting server...
echo  Open your browser at:  http://127.0.0.1:5000
echo  Press Ctrl+C to stop.
echo.

python run.py

pause
