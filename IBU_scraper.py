from flask import Flask, request, render_template, jsonify, Response
from utils import name_to_color
from datetime import datetime, timedelta
import pandas as pd
import os
import hashlib
import queue
import json
import sys
import signal
import atexit
from Google_Drive_importer import (
    ensure_files_available, 
    get_latest_file_path
)
import tempfile

# Use temporary directory for cloud deployment
if os.getenv('RENDER'):  # Render sets this environment variable
    DATA_FOLDER = tempfile.mkdtemp()
    print(f"Using temporary storage for cloud deployment: {DATA_FOLDER}")
else:
    DATA_FOLDER = os.getenv("DATA_FOLDER", "Scraped_Team_Info")

progress_queue = queue.Queue()
layout_height = 550
layout_width = 1000
aspect_ratio = layout_height / layout_width

def name_to_color(name):
    # Hash the name to get a consistent value
    hash_object = hashlib.md5(name.encode())
    hex_color = "#" + hash_object.hexdigest()[:6]
    return hex_color

def get_latest_csv_file():
    """
    Get the latest CSV file from Google Drive, downloading if necessary
    """
    try:
        # Get the latest file from Google Drive with timestamp
        file_path, message, file_timestamp = get_latest_file_path()
        if file_path and os.path.exists(file_path):
            # Extract date from filename
            filename = os.path.basename(file_path)
            date_str = filename.replace("sheepit_team_points_", "").replace(".csv", "")
            return file_path, date_str, file_timestamp
        else:
            return None, None, None
            
    except Exception as e:
        print(f"Error getting latest file from Google Drive: {str(e)}")
        return None, None, None

def get_time_ago_string(file_timestamp):
    """Convert timestamp to 'X time ago' format"""
    if not file_timestamp:
        return "Recently"
    
    try:
        current_time = datetime.now()
        time_diff = current_time - file_timestamp
        
        total_seconds = int(time_diff.total_seconds())
        
        # Calculate time units
        if total_seconds < 60:
            return "Just now" if total_seconds < 10 else f"{total_seconds} seconds ago"
        
        minutes = total_seconds // 60
        if minutes < 60:
            return "1 minute ago" if minutes == 1 else f"{minutes} minutes ago"
        
        hours = minutes // 60
        if hours < 24:
            return "1 hour ago" if hours == 1 else f"{hours} hours ago"
        
        days = hours // 24
        if days < 30:
            return "1 day ago" if days == 1 else f"{days} days ago"
        
        months = days // 30
        if months < 12:
            return "1 month ago" if months == 1 else f"{months} months ago"
        
        years = months // 12
        return "1 year ago" if years == 1 else f"{years} years ago"
        
    except Exception as e:
        print(f"Error calculating time ago: {e}")
        return "Recently"

def get_chart_total():
    # Use Google Drive importer to ensure the latest file is available
    file_requests = [
        {'type': 'latest'}
    ]
    
    result = ensure_files_available(file_requests)
    if not result['success']:
        error_msg = "Latest file not available from Google Drive."
        if result['errors']:
            error_msg += f" Errors: {'; '.join(result['errors'])}"
        return {"error": error_msg}
    
    if len(result['files']) == 0:
        return {"error": "No files could be downloaded from Google Drive."}
    
    # Use the downloaded file
    file = result['files'][0]
    
    if not os.path.exists(file):
        return {"error": "Downloaded file is not accessible."}
    
    try:
        # Load CSV
        df = pd.read_csv(file)
        
        # Check if file is empty
        if df.empty:
            return {"error": "Data file is empty."}
        
        df.columns = df.columns.str.strip()
        df = df.rename(columns={"name": "Member", "points": "Points"})
        
        # Check if required columns exist
        if "Member" not in df.columns or "Points" not in df.columns:
            return {"error": "Data file missing required columns (Member, Points)."}
        
        # Check if there's any data
        if len(df) == 0:
            return {"error": "No data available in file."}
        
        member = df["Member"]
        points = df["Points"]
        color = df["Member"].apply(name_to_color)
        return data_for_return(member, points, color)
        
    except Exception as e:
        return {"error": f"Error processing data file: {str(e)}"}

def get_last_week_range():
    today = datetime.today().date()
    last_monday = today - timedelta(days=today.weekday() + 7)
    this_monday = last_monday + timedelta(days=6)
    print(last_monday, this_monday)
    end_date = this_monday.strftime("%Y-%m-%d")
    start_date = last_monday.strftime("%Y-%m-%d")
    
    # Use Google Drive importer to ensure files are available
    file_requests = [
        {'type': 'single_date', 'date': start_date},
        {'type': 'single_date', 'date': end_date}
    ]
    
    result = ensure_files_available(file_requests)
    if not result['success']:
        error_msg = "Required files not available for the selected week range."
        if result['errors']:
            error_msg += f" Errors: {'; '.join(result['errors'])}"
        return {"error": error_msg}
    
    if len(result['files']) < 2:
        return {"error": f"Could not download both required files. Only got {len(result['files'])} files."}
    
    # Use the actual downloaded file paths
    file_start = result['files'][0] if start_date in result['files'][0] else result['files'][1]
    file_end = result['files'][1] if end_date in result['files'][1] else result['files'][0]
    
    # Verify files exist
    if not os.path.exists(file_start) or not os.path.exists(file_end):
        return {"error": "Downloaded files are not accessible."}
    
    return standardize_range_formats(file_start, file_end)

def get_last_month_range():
    today = datetime.today().date()
    first_of_this_month = today.replace(day=1)
    last_month_end = first_of_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    end_date = last_month_end.strftime("%Y-%m-%d")
    start_date = last_month_start.strftime("%Y-%m-%d")
    
    # Use Google Drive importer to ensure files are available
    file_requests = [
        {'type': 'single_date', 'date': start_date},
        {'type': 'single_date', 'date': end_date}
    ]
    
    result = ensure_files_available(file_requests)
    if not result['success']:
        error_msg = "Required files not available for the selected month range."
        if result['errors']:
            error_msg += f" Errors: {'; '.join(result['errors'])}"
        return {"error": error_msg}
    
    if len(result['files']) < 2:
        return {"error": f"Could not download both required files. Only got {len(result['files'])} files."}
    
    # Use the actual downloaded file paths
    file_start = result['files'][0] if start_date in result['files'][0] else result['files'][1]
    file_end = result['files'][1] if end_date in result['files'][1] else result['files'][0]
    
    # Verify files exist
    if not os.path.exists(file_start) or not os.path.exists(file_end):
        return {"error": "Downloaded files are not accessible."}
    
    return standardize_range_formats(file_start, file_end)

def get_last_year_range():
    today = datetime.today().date()
    last_year = today.year - 1
    last_year_start = datetime(last_year, 1, 1).date()
    last_year_end = datetime(last_year, 12, 31).date()
    end_date = last_year_end.strftime("%Y-%m-%d")
    start_date = last_year_start.strftime("%Y-%m-%d")
    
    # Use Google Drive importer to ensure files are available
    file_requests = [
        {'type': 'single_date', 'date': start_date},
        {'type': 'single_date', 'date': end_date}
    ]
    
    result = ensure_files_available(file_requests)
    if not result['success']:
        error_msg = "Required files not available for the selected year range."
        if result['errors']:
            error_msg += f" Errors: {'; '.join(result['errors'])}"
        return {"error": error_msg}
    
    if len(result['files']) < 2:
        return {"error": f"Could not download both required files. Only got {len(result['files'])} files."}
    
    # Use the actual downloaded file paths
    file_start = result['files'][0] if start_date in result['files'][0] else result['files'][1]
    file_end = result['files'][1] if end_date in result['files'][1] else result['files'][0]
    
    # Verify files exist
    if not os.path.exists(file_start) or not os.path.exists(file_end):
        return {"error": "Downloaded files are not accessible."}
    
    return standardize_range_formats(file_start, file_end)

def get_chart_data_for_range(start_date, end_date):
    # Use Google Drive importer to ensure files are available
    file_requests = [
        {'type': 'single_date', 'date': start_date.strftime("%Y-%m-%d")},
        {'type': 'single_date', 'date': end_date.strftime("%Y-%m-%d")}
    ]
    
    result = ensure_files_available(file_requests)
    if not result['success']:
        error_msg = "Required files not available for the selected range."
        if result['errors']:
            error_msg += f" Errors: {'; '.join(result['errors'])}"
        return {"error": error_msg}

    if len(result['files']) < 2:
        return {"error": f"Could not download both required files. Only got {len(result['files'])} files."}

    # Use the actual downloaded file paths
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    
    file_start = result['files'][0] if start_date_str in result['files'][0] else result['files'][1]
    file_end = result['files'][1] if end_date_str in result['files'][1] else result['files'][0]

    # Verify files exist
    if not os.path.exists(file_start) or not os.path.exists(file_end):
        return {"error": "Downloaded files are not accessible."}

    return standardize_range_formats(file_start, file_end)

def standardize_range_formats(file_start_raw, file_end_raw):
    # Load CSVs
    df_start = pd.read_csv(file_start_raw)
    df_end = pd.read_csv(file_end_raw)

    # Clean and standardize column names
    df_start.columns = df_start.columns.str.strip()
    df_end.columns = df_end.columns.str.strip()

    # Rename columns to match
    df_start = df_start.rename(columns={"name": "Member", "points": "Points"})
    df_end = df_end.rename(columns={"name": "Member", "points": "Points"})

    
    # Find new members in end that are not in start
    new_members = set(df_end["Member"]) - set(df_start["Member"])
    if new_members:
        # Create DataFrame for new members with 0 points at start
        new_rows = pd.DataFrame({
            "Member": list(new_members),
            "Points": [0] * len(new_members)
        })
        # Append to df_start
        df_start = pd.concat([df_start, new_rows], ignore_index=True)

    # Merge and calculate difference
    merged = pd.merge(df_end, df_start, on="Member", suffixes=("_end", "_start"))
    merged["Delta"] = merged["Points_end"] - merged["Points_start"]
    #merged = merged[merged["Delta"] > 0] # Uncomment to filter out non-positive/0 points members
    color = merged["Member"].apply(name_to_color)
    member = merged["Member"]
    points = merged["Delta"]

    # Return data in pie chart format
    return data_for_return(member, points, color)

def data_for_return(data_member, data_points, color_data):
    return {
        "data": [
        {
            "type": "pie",
            "labels": data_member.tolist(),
            "values": data_points.tolist(),
            "hole": 0.6,
            "text": get_custom_text(data_points, data_member),
            "textinfo": "text",
            "textposition": "outside",
            "hoverinfo": "label+percent+value",
            "hovertemplate": "<b>%{label}</b><br>" +
                           "Points: %{value:,}<br>" +
                           "Percentage: %{percent}<br>" +
                           "<extra></extra>",
            "marker": {
                "colors": color_data.tolist(),
                "line": {
                    "color": "rgba(255, 255, 255, 0.2)",
                    "width": 1
                }
            },
            "automargin": False,
            "domain": {"x": [0, 1], "y": [0, 1]},
        }
    ],
    "layout": {
        "width": layout_width,
        "height": layout_height, 
        "margin": {"t": 30, "b": 30, "l": 0, "r": 0},
        "showlegend": True,
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "annotations": [
            {
                "text": f"<b>Total Points</b><br><br><span style='font-size:24px; color:#e06150'>{sum(data_points):,}</span>",
                "x": 0.5,
                "y": 0.55,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {
                    "size": 14,
                    "color": "white",
                    "family": "Inter, Arial, sans-serif"
                },
                "align": "center"
            },
            {
                "text": f"Active Members: {len([x for x in data_points if x > 0])}",
                "x": 0.5,
                "y": 0.4,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {
                    "size": 12,
                    "color": "rgba(255, 255, 255, 0.7)",
                    "family": "Inter, Arial, sans-serif"
                },
                "align": "center"
            }
        ],
        "shapes": [
            {
                "type": "circle",
                "xref": "paper",
                "yref": "paper",
                "x0": 0.325,
                "y0": 0.20,
                "x1": 1-0.325,
                "y1": 0.80,
                "line": {"color": "ffffff", "width": 3},
                "fillcolor": "rgba(0,0,0,0)"
            },
            {
                "type": "circle",
                "xref": "paper",
                "yref": "paper",
                "x0": 0.207,
                "y0": 0,
                "x1": 1-0.207,
                "y1": 1,
                "line": {"color": "ffffff", "width": 3},
                "fillcolor": "rgba(0,0,0,0)"
            }
        ],
        "font": {
            "color": "white",
            "family": "Inter, Arial, sans-serif",
            "size": 14
        },
        "legend": {
            "title": {
                "text": "<b style='color:#e06150; font-size:16px'>👥 Team Members</b>",
                "font": {
                    "color": "#e06150",
                    "size": 16,
                    "family": "Inter, Arial, sans-serif"
                }
            },
            "orientation": "v",
            "xanchor": "left",
            "x": 1,
            "y": 0,
            "bgcolor": "rgba(42, 42, 42, 0.8)",
            "bordercolor": "rgba(224, 97, 80, 0.3)",
            "borderwidth": 1,
            "font": {
                "color": "white",
                "size": 12,
                "family": "Inter, Arial, sans-serif"
            },
            "itemsizing": "constant",
            "itemwidth": 50
        }
    },
    "config": {
        "displaylogo": False,
        "displayModeBar": False,
        "showTips": False
    }
}

def get_custom_text(values, labels):
    total = sum(values)
    result = []
    for i, v in enumerate(values):
        if v == 0 or total == 0:
            result.append("")
        else:
            percent = (v / total) * 100
            if percent >= 0.95:
                result.append(f"   {labels[i]} ({percent:.1f}%)   ")
            else:
                result.append("")
    return result

app = Flask(__name__) #. .venv/bin/activate

@app.route('/')
def index():
    file_path, date_str, file_timestamp = get_latest_csv_file()
    if not file_path or not date_str:
        latest_file = "No data"
        latest_date = "No data"
        time_ago = "No recent data"
    else:
        # Format the file string if possible
        try:
            latest_file = os.path.abspath(file_path)
            latest_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
            time_ago = get_time_ago_string(file_timestamp)
        except Exception:
            latest_file = file_path
            latest_date = date_str
            time_ago = "Recently"
    
    print(f"Latest file: {latest_file}, Date: {latest_date}, Time ago: {time_ago}")
    return render_template('index_IBU.html', 
                         saved_file=latest_file, 
                         latest_date=latest_date,
                         time_ago=time_ago)

@app.route("/get_chart_data")
def get_chart_data():
    chart_type = request.args.get("type")
    start = request.args.get("start")
    end = request.args.get("end")

    if chart_type == "last_week":
        data = get_last_week_range()
        if not data or "error" in data:
            return jsonify({"error": "Not enough data available for the selected range."}), 400
        return jsonify(data)
    elif chart_type == "last_month":
        data = get_last_month_range()
        if not data or "error" in data:
            return jsonify({"error": "Not enough data available for the selected range."}), 400
        return jsonify(data)
    elif chart_type == "last_year":
        data = get_last_year_range()
        if not data or "error" in data:
            return jsonify({"error": "Not enough data available for the selected range."}), 400
        return jsonify(data)
    elif chart_type == "custom" and start and end:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
        data = get_chart_data_for_range(start_date, end_date)
        if not data or "error" in data:
            return jsonify({"error": "Not enough data available for the selected range."}), 400
        return jsonify(data)
    elif chart_type == "total":
        data = get_chart_total()
        if not data or "error" in data:
            return jsonify({"error": "Not enough data available."}), 400
        return jsonify(data)
    else:
        return jsonify({"error": "Invalid request"}), 400

@app.route("/visualization")
def visualization():
    # Get date and time info from the latest file for display
    latest_date_fmt = "No data"
    time_ago = "No recent data"
    try:
        # Try to get the latest file info for date formatting
        file_path, date_str, file_timestamp = get_latest_csv_file()
        if date_str:
            latest_date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
            time_ago = get_time_ago_string(file_timestamp)
    except Exception:
        latest_date_fmt = "Recent data"
        time_ago = "Recently"
    
    # Don't pre-load chart data - let the frontend handle it via AJAX
    return render_template("graphs_modern.html", 
                         labels=[], 
                         values=[], 
                         colors=[], 
                         latest_date=latest_date_fmt,
                         time_ago=time_ago)

def flask_progress_callback(msg, progress_percent, latest_date=None, saved_file=None):
    payload = {"msg": msg, "percent": progress_percent}
    if latest_date is not None:
        payload["latest_date"] = latest_date
    if saved_file is not None:
        payload["saved_file"] = saved_file
    progress_queue.put(json.dumps(payload))

@app.route('/progress_stream')
def progress_stream():
    def event_stream():
        while True:
            message = progress_queue.get()
            yield f"data: {message}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/drive_status')
def drive_status():
    """Check Google Drive connection and list available files"""
    try:
        from Google_Drive_importer import test_drive_connection, list_all_available_files, get_available_dates
        
        # Test connection
        success, message = test_drive_connection()
        
        if success:
            # Get file information
            file_info = list_all_available_files()
            available_dates = get_available_dates()
            
            return jsonify({
                'success': True,
                'connection_status': message,
                'drive_files_count': file_info['drive_count'],
                'local_files_count': file_info['local_count'],
                'drive_files': file_info['drive_files'][:10],  # Show first 10 files
                'available_dates': available_dates[:10],  # Show first 10 dates
                'latest_date': available_dates[0] if available_dates else None
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Error checking drive status: {str(e)}"
        })

@app.route('/sync_files')
def sync_files():
    """Sync recent files from Google Drive"""
    try:
        from Google_Drive_importer import sync_latest_files
        
        days_back = request.args.get('days', 7, type=int)
        results = sync_latest_files(days_back)
        
        successful_files = [r for r in results if r['success']]
        failed_files = [r for r in results if not r['success']]
        
        return jsonify({
            'success': True,
            'total_requested': len(results),
            'successful': len(successful_files),
            'failed': len(failed_files),
            'successful_files': [r['path'] for r in successful_files],
            'failed_dates': [r['date'] for r in failed_files],
            'messages': [r['message'] for r in results]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Error syncing files: {str(e)}"
        })

@app.route('/clear_cache')
def clear_cache():
    """Manually clear the local file cache"""
    try:
        if os.path.exists(DATA_FOLDER):
            files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
            file_count = len(files)
            
            # Remove only CSV files, keep the folder
            for file in files:
                file_path = os.path.join(DATA_FOLDER, file)
                os.remove(file_path)
            
            return jsonify({
                'success': True,
                'message': f"Successfully cleared cache. Removed {file_count} files."
            })
        else:
            return jsonify({
                'success': True,
                'message': "Cache folder was already empty."
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Error clearing cache: {str(e)}"
        })

def cleanup_on_exit():
    """Clean up downloaded files when the app exits"""
    try:
        if os.path.exists(DATA_FOLDER):
            files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
            if files:
                print(f"\nCleaning up {len(files)} temporary files in {DATA_FOLDER}...")
                for file in files:
                    file_path = os.path.join(DATA_FOLDER, file)
                    os.remove(file_path)
                print("Cleanup complete!")
            else:
                print(f"\nNo temporary files to clean up in {DATA_FOLDER}")
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutting down gracefully...")
    cleanup_on_exit()
    sys.exit(0)

# Register cleanup functions
atexit.register(cleanup_on_exit)
signal.signal(signal.SIGINT, signal_handler)

@app.route('/check_drive_connection')
def check_drive_connection():
    """Check Google Drive connection status by testing folder access"""
    try:
        # Import the Google Drive test function
        from Google_Drive_importer import test_drive_connection
        
        # Simple connection test - just check if we can list files in the folder
        success, message = test_drive_connection()
        
        if success:
            return jsonify({
                "connected": True,
                "message": message
            })
        else:
            return jsonify({
                "connected": False,
                "message": message
            })
            
    except ImportError:
        return jsonify({
            "connected": False,
            "message": "Google Drive module not found"
        })
    except Exception as e:
        print(f"Google Drive connection error: {str(e)}")
        return jsonify({
            "connected": False,
            "error": str(e),
            "message": "Google Drive connection failed"
        })

@app.route('/test_connection')
def test_connection_page():
    """Serve a test page for debugging connection issues"""
    return '''<!DOCTYPE html>
<html>
<head>
    <title>Connection Test</title>
</head>
<body>
    <h1>Google Drive Connection Test</h1>
    <div id="result">Testing...</div>
    <button onclick="testConnection()">Test Again</button>
    
    <script>
        async function testConnection() {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = 'Testing...';
            
            try {
                console.log('Making request to /check_drive_connection');
                const response = await fetch('/check_drive_connection');
                console.log('Response:', response);
                
                if (response.ok) {
                    const data = await response.json();
                    console.log('Data:', data);
                    
                    resultDiv.innerHTML = `
                        <h2>Response received:</h2>
                        <p><strong>Connected:</strong> ${data.connected}</p>
                        <p><strong>Message:</strong> ${data.message}</p>
                        <p><strong>Raw JSON:</strong> ${JSON.stringify(data)}</p>
                    `;
                } else {
                    resultDiv.innerHTML = `<p style="color: red;">HTTP Error: ${response.status} ${response.statusText}</p>`;
                }
            } catch (error) {
                console.error('Error:', error);
                resultDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            }
        }
        
        // Test on load
        testConnection();
    </script>
</body>
</html>'''

@app.route('/warmup_drive')
def warmup_drive():
    """Warmup Google Drive connection"""
    try:
        from Google_Drive_importer import authenticate_drive_api
        
        # Initialize the drive service
        drive_service = authenticate_drive_api()
        
        return jsonify({
            "success": True,
            "message": "Google Drive service initialized"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/get_simple_stats')
def get_simple_stats():
    """Get basic stats without full chart processing"""
    try:
        file_path, date_str, file_timestamp = get_latest_csv_file()
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                "error": "No data file available",
                "stats": {
                    "total_points": 0,
                    "active_members": 0,
                    "top_performers": []
                }
            })
        
        # Load CSV directly
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
        df = df.rename(columns={"name": "Member", "points": "Points"})
        
        # Calculate basic stats
        total_points = int(df["Points"].sum())
        active_members = len(df[df["Points"] > 0])
        
        # Get top 5 performers
        top_performers = df[df["Points"] > 0].nlargest(5, "Points").to_dict('records')
        
        return jsonify({
            "success": True,
            "stats": {
                "total_points": total_points,
                "active_members": active_members,
                "top_performers": [
                    {
                        "name": performer["Member"],
                        "points": int(performer["Points"])
                    } for performer in top_performers
                ]
            }
        })
        
    except Exception as e:
        print(f"Error getting simple stats: {str(e)}")
        return jsonify({
            "error": f"Error loading stats: {str(e)}",
            "stats": {
                "total_points": 0,
                "active_members": 0,
                "top_performers": []
            }
        })

# Flask startup
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))  # Render provides PORT env var
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    print("Starting IBU Dashboard...")
    print(f"Access the dashboard at: http://localhost:{port}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)