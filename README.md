# Traffic Accident Analysis Dashboard

Simple Flask app to upload CSV files of accident records and explore patterns by weather, road condition, time of day, and hotspots.

Quick start

1. Create a virtual environment and install dependencies:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the app:

```bash
python app.py
```

3. Open http://127.0.0.1:5000 in your browser and go to Upload.

Notes
- Upload a CSV with columns for time/date, weather and road condition. The processor will try to discover common column names.
- Sample CSVs are included in the `samples` folder.
