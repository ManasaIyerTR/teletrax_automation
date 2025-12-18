**Teletrax Presentation Generator**

Automated tool that turns Teletrax exports into a client-ready PowerPoint in minutes using a simple Streamlit web page (runs on your computer).

**What it does**

- Builds a formatted PowerPoint report from Teletrax data exports
- Supports single-channel and multi-channel reporting (where applicable)
- Generates charts and summary insights based on your uploaded files
- Full step-by-step user guide: https://docs.google.com/document/d/1jhVb3abKpw0LboDQ8VIJrc-0P9GUWFtY9Vnuvzpnq-Q/edit?tab=t.0

**Quick start (non-technical)**

- Install Python (one-time setup)
  - You need a Python environment to run this tool.
  - Recommended: Python 3.11
  - Also OK: Python 3.10+

- Check if Python is installed:
  - Windows:
    - python --version
  - Mac:
    - python3 --version
  - If you don't have Python (or it's older than 3.10), install Python 3.11 and retry the command above.

- Get the code
  - Clone or download this repository to your computer.

- Install dependencies
  - Open Command Prompt (Windows) or Terminal (Mac) IN the project folder (the folder that contains app.py and requirements.txt), then run:
     - pip install -r requirements.txt
- Run the app
  - Run:
   - streamlit run app.py

- Then open (or keep open) your browser at:
  - http://localhost:8501
  - "localhost" means it's running on your computer (not on the internet).

**How to use (high level)**

- Open the app in your browser
- Choose report settings in the sidebar (presentation type / channel details)
- Upload the required Teletrax export files
- Click "Generate Presentation"
- Download the finished .pptx
- For exact Teletrax export steps and required columns, use the Google Doc guide link above.

**Data files you'll upload (summary)**

You'll upload 2–3 Teletrax exports depending on the report type.

Typical inputs include:

- Time series / trend file (monthly trend over time)
- Distribution file (e.g., country/location breakdown)
- Slug / headline file (raw text used to compute top stories)
- For multi-channel reporting, you may upload one distribution file per channel.

**Note:** The app expects specific column names. Use the Google Doc guide to export the correct format.

**Troubleshooting**#

1. App won't start / "streamlit not found"
  - Reinstall dependencies:
  - pip install -r requirements.txt

2. Charts not rendering or image export issues
  - Install Kaleido (if not already included by requirements):
  - pip install kaleido

3. PowerPoint generation fails
  - Double-check:
   - File type is .xlsx or .csv
   - Columns match the expected names (see user guide)
   - Files aren't empty and don't contain only headers

**Project structure**

teletrax-automation/
- app.py
- requirements.txt
- config/
  - colors.py
- utils/
  - init.py
  - data_processing.py
  - chart_generator.py
  - ppt_generator.py
- README.md

**Customization (for developers)**

1. Colors:
- Edit config/colors.py

2. Chart styling:
- Modify utils/chart_generator.py

3. Slide layout / formatting:
- Update utils/ppt_generator.py

**Version history**

v1.0 (2025): Initial release (Streamlit app + PPT export)
