#!/usr/bin/env python3
"""
Startup script for the Pre-Demolition Audit Generator.
Run with:  python run.py
"""
import subprocess
import sys
import os


def check_and_install():
    """Install requirements if not already installed."""
    try:
        import flask
        import weasyprint
        import matplotlib
        import anthropic
    except ImportError:
        print("Installing required packages...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt',
            '--break-system-packages', '-q'
        ])
        print("Packages installed.\n")


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    check_and_install()
    from app import app
    port = int(os.environ.get('PORT', 5000))
    print(f"\n  ✅  Pre-Demolition Audit Generator")
    print(f"  📋  Open in your browser:  http://127.0.0.1:{port}")
    print(f"  🛑  Press Ctrl+C to stop\n")
    app.run(debug=False, host='127.0.0.1', port=port)
