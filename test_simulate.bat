@echo off
cd /d "%~dp0"
title Hanet FaceID Web App Simulator
cls

echo =======================================================
echo    GIẢ LẬP GỬI DỮ LIỆU CHECK-IN FACEID TỚI WEB APP
echo =======================================================
echo.

python test_webhook.py
echo.
pause
