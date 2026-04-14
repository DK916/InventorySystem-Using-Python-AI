#!/bin/bash
echo ""
echo "============================================================"
echo "  InvenCore — Role-Based Inventory Management System"
echo "============================================================"
echo ""
echo "  Starting server on http://localhost:8765"
echo "  Press Ctrl+C to stop"
echo ""

# Try python3 first, then python
if command -v python3 &>/dev/null; then
    python3 inventory_system.py
elif command -v python &>/dev/null; then
    python inventory_system.py
else
    echo "ERROR: Python not found."
    echo "Please install Python 3.7+ from https://www.python.org"
fi
