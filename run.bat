@echo off
title InvenCore — Inventory Management System
echo.
echo  ============================================================
echo   InvenCore — Role-Based Inventory Management System
echo  ============================================================
echo.
echo  Starting server on http://localhost:8765
echo  Press Ctrl+C to stop the server
echo.
python inventory_system.py
if errorlevel 1 (
    echo.
    echo  ERROR: Python not found. Please install Python 3.7+
    echo  Download from: https://www.python.org/downloads/
    echo.
    pause
)
