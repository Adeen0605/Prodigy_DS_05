from flask import Flask, render_template, request, redirect, url_for, flash
import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'csv'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'dev-secret'

analyses = {}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_col_like(df, candidates):
    cols = list(df.columns)
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        for k in lower:
            if cand in k:
                return lower[k]
    return None


def _extract_hour(df):
    time_col = _get_col_like(df, ['time', 'accident_time', 'hour'])
    datetime_col = _get_col_like(df, ['date_time', 'datetime', 'timestamp', 'date/time'])
    if 'hour' in df.columns:
        try:
            return df['hour'].astype(int).clip(0, 23)
        except Exception:
            pass
    if time_col:
        try:
            ser = pd.to_datetime(df[time_col], errors='coerce')
            if ser.dt.hour.notna().any():
                return ser.dt.hour.fillna(0).astype(int)
        except Exception:
            pass
    if datetime_col:
        try:
            ser = pd.to_datetime(df[datetime_col], errors='coerce')
            if ser.dt.hour.notna().any():
                return ser.dt.hour.fillna(0).astype(int)
        except Exception:
            pass
    for cand in ['hour', 'Hour']:
        if cand in df.columns:
            try:
                return df[cand].astype(int).clip(0, 23)
            except Exception:
                pass
    return pd.Series(np.zeros(len(df), dtype=int))


def process_csv(path):
    df = pd.read_csv(path)
    original_columns = list(df.columns)

    weather_col = _get_col_like(df, ['weather', 'weather_condition', 'weathertype'])
    road_col = _get_col_like(df, ['road', 'surface', 'road_surface', 'road_condition', 'roadcondition'])

    if weather_col is None:
        df['weather_condition'] = 'Unknown'
    else:
        df['weather_condition'] = df[weather_col].astype(str).fillna('Unknown')

    if road_col is None:
        df['road_condition'] = 'Unknown'
    else:
        df['road_condition'] = df[road_col].astype(str).fillna('Unknown')

    df['hour'] = _extract_hour(df)

    lat_col = _get_col_like(df, ['latitude', 'lat'])
    lon_col = _get_col_like(df, ['longitude', 'lon', 'lng'])

    weather_counts = df['weather_condition'].value_counts().reset_index()
    weather_counts.columns = ['weather', 'count']
    fig_weather = px.bar(weather_counts, x='weather', y='count', color='weather', title='Accidents by Weather Condition')

    road_counts = df['road_condition'].value_counts().reset_index()
    road_counts.columns = ['road', 'count']
    fig_road = px.pie(road_counts, values='count', names='road', title='Road Surface / Condition')

    time_series = df.groupby('hour').size().reset_index(name='count').sort_values('hour')
    fig_time = px.line(time_series, x='hour', y='count', markers=True, title='Accidents by Hour of Day')

    hotspots = None
    if lat_col and lon_col:
        try:
            df['_lat_round'] = df[lat_col].round(3)
            df['_lon_round'] = df[lon_col].round(3)
            hotspots = df.groupby(['_lat_round', '_lon_round']).size().reset_index(name='count').sort_values('count', ascending=False).head(10)
        except Exception:
            hotspots = None

    weather_div = pio.to_html(fig_weather, include_plotlyjs=False, full_html=False)
    road_div = pio.to_html(fig_road, include_plotlyjs=False, full_html=False)
    time_div = pio.to_html(fig_time, include_plotlyjs=False, full_html=False)

    table_html = df.head(200).to_html(classes='table table-striped', index=False, border=0)

    result = {
        'filename': os.path.basename(path),
        'original_columns': original_columns,
        'weather_div': weather_div,
        'road_div': road_div,
        'time_div': time_div,
        'hotspots': hotspots.to_dict(orient='records') if hotspots is not None else [],
        'table_html': table_html,
        'row_count': len(df)
    }
    return result


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            try:
                analysis = process_csv(save_path)
                analyses[filename] = analysis
                return redirect(url_for('analysis', filename=filename))
            except Exception as e:
                flash(f'Failed to process file: {e}')
                return redirect(request.url)
    samples = []
    sample_dir = os.path.join(BASE_DIR, 'samples')
    if os.path.exists(sample_dir):
        samples = [f for f in os.listdir(sample_dir) if f.lower().endswith('.csv')]
    return render_template('upload.html', samples=samples)


@app.route('/analysis/<filename>')
def analysis(filename):
    if filename not in analyses:
        flash('No analysis found for that file. Please upload first.')
        return redirect(url_for('upload'))
    a = analyses[filename]
    return render_template('analysis.html', analysis=a)


if __name__ == '__main__':
    app.run(debug=True)
