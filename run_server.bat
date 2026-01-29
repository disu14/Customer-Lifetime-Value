@echo off
cd /d "%~dp0"
echo Starting CLV server...
echo Open http://localhost:8000 in your browser.
echo Press Ctrl+C to stop.
python backend/serve.py
pause
