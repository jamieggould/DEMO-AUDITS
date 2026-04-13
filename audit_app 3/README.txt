
  ============================================================
   PRE-DEMOLITION AUDIT GENERATOR  |  Lawmens
   Powered by Flask + WeasyPrint + Anthropic AI
  ============================================================

  QUICK START
  ──────────────────────────────────────────────────────────
  Windows:   Double-click  START_WINDOWS.bat
  Mac/Linux: Double-click  START_MAC.command
             (or: python3 run.py)

  Then open your browser at:
    http://127.0.0.1:5000


  REQUIREMENTS
  ──────────────────────────────────────────────────────────
  • Python 3.10 or later  →  https://python.org/downloads
  • Internet connection on first run (to install packages)

  The startup scripts install all required packages
  automatically on first run.


  USING THE APP
  ──────────────────────────────────────────────────────────
  The app has 7 steps:

  Step 1 · Project Details
    Enter job address, client name, report number, date,
    building type and building description.

  Step 2 · Report Team
    Enter the names, positions and photos of the person
    who prepared and the person who authorised the report.

  Step 3 · Photos & Floor Plans
    Upload the building exterior photo and any floor plan
    drawings (JPG/PNG). Add one row per floor.

  Step 4 · Key Waste Products (KWP)
    Enter each material in the building with its EWC code,
    volume, weight, carbon factor, and reuse/recycling
    percentages. Pre-filled with common materials — edit
    as needed.

  Step 5 · Material Reuse Items
    For the final "Material Reuse" section, add individual
    items with photos, reuse potential (High/Medium/Low)
    and risk factors.

  Step 6 · Report Text & AI Generation
    Either type your text manually, OR enter your Anthropic
    API key (sk-ant-...) and click "✨ AI Generate" next
    to each section to auto-generate professional text.

    Get an API key at: https://console.anthropic.com

  Step 7 · Generate
    Click "Generate PDF Report" — the report will download
    automatically (20–40 seconds with AI generation).


  ADDING YOUR LAWMENS LOGO
  ──────────────────────────────────────────────────────────
  Replace the file:  static/images/lawmens_logo.png
  with your actual Lawmens logo PNG file.
  (Recommended: PNG with transparent background, ~300×100px)


  CUSTOMISING BOILERPLATE TEXT
  ──────────────────────────────────────────────────────────
  The 14 boilerplate pages (Introduction through Methodology)
  are in:  templates/report.html
  Search for the page headings to find and update any text.


  TROUBLESHOOTING
  ──────────────────────────────────────────────────────────
  "WeasyPrint error": Install GTK libraries
    Windows:  https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
    Mac:      brew install pango
    Linux:    sudo apt install libpango-1.0-0

  "Module not found": Run  pip install -r requirements.txt

  Port already in use: Change PORT in a .env file, e.g.:
    PORT=5001


  ============================================================
