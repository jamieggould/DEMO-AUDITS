#!/bin/bash
cd "$(dirname "$0")"
echo ""
echo " ============================================"
echo "  Pre-Demolition Audit Generator - Lawmens"
echo " ============================================"
echo ""
echo " Installing required packages (first run only)..."
python3 -m pip install flask weasyprint matplotlib anthropic Pillow python-dotenv -q
echo ""
echo " Starting server..."
echo " Open your browser at:  http://127.0.0.1:5000"
echo " Press Ctrl+C to stop."
echo ""
python3 run.py
