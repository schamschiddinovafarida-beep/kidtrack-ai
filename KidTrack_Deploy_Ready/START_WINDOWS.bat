@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (set PY=py) else (set PY=python)
%PY% -m pip install -r requirements.txt
if errorlevel 1 (echo Python or pip not available. See README_RU.txt & pause & exit /b 1)
echo.
echo KidTrack will open at http://127.0.0.1:5000
echo Keep this window open while using the site.
start http://127.0.0.1:5000
%PY% server.py
pause
