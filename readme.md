**Teletrax Presentation Generator**

Automated tool for generating client presentations from Teletrax tracking data.

**Features**

✅ Single & Multi-Channel Support: Generate presentations for one or multiple channels

✅ Automated Chart Generation: Time series, pie charts with exact color matching

✅ Slug Line Analysis: Automatic extraction of top 3 most-used stories

✅ PowerPoint Export: Professional slides ready for client delivery

✅ Web Interface: Easy-to-use Streamlit application

**Installation**

Clone or download this repository

**Install dependencies:**

pip install -r requirements.txt
Run the application:

streamlit run app.py

Open your browser to http://localhost:8501

**USAGE**

Data File Requirements

Time Series Data (Top Left Chart):

Columns: Month, # Assets

Format: Excel (.xlsx) or CSV

**Country Distribution (Top Right Chart):**

Columns: Location code (ISO country codes), # Hits

Format: Excel (.xlsx) or CSV

**Slug Line Data (Bottom Right):**

Column: Headline/Slug text (raw data, will be counted automatically)

Format: Excel (.xlsx) or CSV

**Multi-Channel Data (if applicable):**

Same format as Country Distribution

One file per channel

**STEPS**

Configure presentation type and channel details in the sidebar

Enter stats (edits, lives, countries, duration)

Upload all required data files

Click "Generate Presentation"

Preview charts in the web interface

Download the PowerPoint file

**Project Structure**

teletrax-automation/

├── app.py                     # Main Streamlit application

├── requirements.txt            # Python dependencies

├── config/

│   └── colors.py              # Color palette configuration

├── utils/

│   ├── __init__.py

│   ├── data_processing.py     # Data loading and processing

│   ├── chart_generator.py     # Plotly chart generation

│   └── ppt_generator.py       # PowerPoint creation

└── README.md                   # This file


**CUSTOMISATION**

**Colors**

Edit config/colors.py to modify the color palette.

**Chart Styling**

Modify functions in utils/chart_generator.py to adjust chart appearance.

**Slide Layout**

Update utils/ppt_generator.py to change PowerPoint positioning and formatting.

**TROUBLESHOOTING**

**Charts not displaying:**

Ensure kaleido is installed: pip install kaleido

**PowerPoint generation fails:**

Check that all data files have the correct column structure

Verify file formats (Excel or CSV only)

**Slug extraction issues:**

Ensure slug data has text

Check for empty rows or invalid data

**Support**

For issues or questions, contact your development team.

Version History
v1.0 (2025): Initial release with single and multi-channel support
