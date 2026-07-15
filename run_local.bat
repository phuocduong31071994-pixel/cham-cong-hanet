@echo off
cd /d "%~dp0"
title Hanet FaceID Attendance Dashboard
cls

echo =======================================================
echo    LAUNCHING HANET FACEID ATTENDANCE DASHBOARD (LOCAL)
echo =======================================================
echo.
echo Opening web browser at http://127.0.0.1:5000 ...
start http://127.0.0.1:5000

echo Starting local Web App...
echo.
echo NOTE: Do NOT close this window! Keep it open to use the website.
echo Press Ctrl+C in this window to stop the server.
echo.

python app.py
pause
