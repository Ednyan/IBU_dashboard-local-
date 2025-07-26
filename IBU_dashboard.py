from flask import Flask, request, render_template, jsonify, Response, session, redirect, url_for, send_file
from datetime import datetime, timedelta
import pandas as pd
import os
import hashlib
import queue
import json
import sys
import signal
import atexit
import glob
import re
import zipfile
import io
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import notification service
try:
    from notification_service import notification_service
    NOTIFICATIONS_ENABLED = True
    print("✅ Email notifications enabled")
except ImportError as e:
    NOTIFICATIONS_ENABLED = False
    print(f"⚠️ Email notifications disabled: {e}")

# Use local data folder
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

def get_csv_files_from_folder():
    """
    Get all CSV files from the local Scraped_Team_Info folder
    """
    try:
        if not os.path.exists(DATA_FOLDER):
            return []
        
        # Get all CSV files matching the pattern sheepit_team_points_YYYY-MM-DD.csv
        pattern = os.path.join(DATA_FOLDER, "sheepit_team_points_*.csv")
        csv_files = glob.glob(pattern)
        
        # Sort by filename (which contains date) to get most recent first
        csv_files.sort(reverse=True)
        
        return csv_files
        
    except Exception as e:
        print(f"Error getting CSV files from folder: {str(e)}")
        return []

def get_latest_csv_file():
    """
    Get the latest CSV file from the local folder
    """
    try:
        csv_files = get_csv_files_from_folder()
        
        if not csv_files:
            return None, None, None
        
        latest_file = csv_files[0]
        
        # Extract date from filename
        filename = os.path.basename(latest_file)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        
        if date_match:
            date_str = date_match.group(1)
            # Get file modification time as timestamp
            file_timestamp = datetime.fromtimestamp(os.path.getmtime(latest_file))
            return latest_file, date_str, file_timestamp
        else:
            return latest_file, "unknown", datetime.fromtimestamp(os.path.getmtime(latest_file))
            
    except Exception as e:
        print(f"Error getting latest file from local folder: {str(e)}")
        return None, None, None

def find_csv_file_by_date(date_str):
    """
    Find a CSV file by date string (YYYY-MM-DD format)
    """
    try:
        target_filename = f"sheepit_team_points_{date_str}.csv"
        target_path = os.path.join(DATA_FOLDER, target_filename)
        
        if os.path.exists(target_path):
            return target_path
        
        # If exact match not found, look for any file containing the date
        csv_files = get_csv_files_from_folder()
        for file in csv_files:
            if date_str in os.path.basename(file):
                return file
        
        return None
        
    except Exception as e:
        print(f"Error finding CSV file by date {date_str}: {str(e)}")
        return None

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

def get_last_day_data():
    """Get chart data showing point differences for the last day (latest file vs previous day file)"""
    try:
        # Get the latest CSV file
        latest_file_path, latest_date_str, _ = get_latest_csv_file()
        
        if not latest_file_path or not latest_date_str:
            return {"error": "No CSV files found for last day calculation."}
        
        # Calculate the previous day
        try:
            latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d").date()
            previous_date = latest_date - timedelta(days=1)
            previous_date_str = previous_date.strftime("%Y-%m-%d")
        except ValueError:
            return {"error": f"Invalid date format in latest file: {latest_date_str}"}
        
        # Find the CSV file for the previous day
        previous_file_path = find_csv_file_by_date(previous_date_str)
        
        if not previous_file_path:
            return {"error": f"Previous day file not found for {previous_date_str}. Cannot calculate last day difference without consecutive day data."}
        
        if not os.path.exists(latest_file_path) or not os.path.exists(previous_file_path):
            return {"error": "Required CSV files not found for last day calculation."}
        
        # Use the existing standardize_range_formats function to calculate differences
        return standardize_range_formats(previous_file_path, latest_file_path)
        
    except Exception as e:
        return {"error": f"Error calculating last day data: {str(e)}"}

def get_chart_total():
    """Get chart data from the latest CSV file in the local folder"""
    try:
        # Get the latest file from local folder
        file_path, date_str, file_timestamp = get_latest_csv_file()
        
        if not file_path or not os.path.exists(file_path):
            return {"error": "No CSV files found in the Scraped_Team_Info folder."}
        
        # Load CSV
        df = pd.read_csv(file_path)
        
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
    """Get chart data for last week using local CSV files"""
    today = datetime.today().date()
    last_monday = today - timedelta(days=today.weekday() + 7)
    this_monday = last_monday + timedelta(days=6)
    print(last_monday, this_monday)
    end_date = this_monday.strftime("%Y-%m-%d")
    start_date = last_monday.strftime("%Y-%m-%d")
    
    # Find the required CSV files in local folder
    file_start = find_csv_file_by_date(start_date)
    file_end = find_csv_file_by_date(end_date)
    
    if not file_start:
        return {"error": f"Start date file not found for {start_date}. Please ensure the CSV file exists in the Scraped_Team_Info folder."}
    
    if not file_end:
        return {"error": f"End date file not found for {end_date}. Please ensure the CSV file exists in the Scraped_Team_Info folder."}
    
    return standardize_range_formats(file_start, file_end)

def get_last_month_range():
    """Get chart data for last month using local CSV files"""
    today = datetime.today().date()
    first_of_this_month = today.replace(day=1)
    last_month_end = first_of_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    end_date = last_month_end.strftime("%Y-%m-%d")
    start_date = last_month_start.strftime("%Y-%m-%d")
    
    # Find the required CSV files in local folder
    file_start = find_csv_file_by_date(start_date)
    file_end = find_csv_file_by_date(end_date)
    
    if not file_start:
        return {"error": f"Start date file not found for {start_date}. Please ensure the CSV file exists in the Scraped_Team_Info folder."}
    
    if not file_end:
        return {"error": f"End date file not found for {end_date}. Please ensure the CSV file exists in the Scraped_Team_Info folder."}
    
    return standardize_range_formats(file_start, file_end)

def get_last_year_range():
    """Get chart data for last year using local CSV files"""
    today = datetime.today().date()
    last_year = today.year - 1
    last_year_start = datetime(last_year, 1, 1).date()
    last_year_end = datetime(last_year, 12, 31).date()
    end_date = last_year_end.strftime("%Y-%m-%d")
    start_date = last_year_start.strftime("%Y-%m-%d")
    
    # Find the required CSV files in local folder
    file_start = find_csv_file_by_date(start_date)
    file_end = find_csv_file_by_date(end_date)
    
    if not file_start:
        return {"error": f"Start date file not found for {start_date}. Please ensure the CSV file exists in the Scraped_Team_Info folder."}
    
    if not file_end:
        return {"error": f"End date file not found for {end_date}. Please ensure the CSV file exists in the Scraped_Team_Info folder."}
    
    return standardize_range_formats(file_start, file_end)

def get_chart_data_for_range(start_date, end_date):
    """Get chart data for a custom date range using local CSV files"""
    # Find the required CSV files in local folder
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    
    file_start = find_csv_file_by_date(start_date_str)
    file_end = find_csv_file_by_date(end_date_str)
    
    if not file_start:
        return {"error": f"Start date file not found for {start_date_str}. Please ensure the CSV file exists in the Scraped_Team_Info folder."}
    
    if not file_end:
        return {"error": f"End date file not found for {end_date_str}. Please ensure the CSV file exists in the Scraped_Team_Info folder."}

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

# Configure Flask session
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'ibu-dashboard-secret-key-change-in-production')

# Admin password configuration
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')  # Default password - change in .env

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

    if chart_type == "last_day":
        data = get_last_day_data()
        if not data or "error" in data:
            return jsonify({"error": "Not enough data available for the last day."}), 400
        return jsonify(data)
    elif chart_type == "last_week":
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

@app.route('/local_status')
def local_status():
    """Check local file status and list available CSV files"""
    try:
        csv_files = get_csv_files_from_folder()
        
        if csv_files:
            # Extract dates from filenames
            available_dates = []
            for file in csv_files:
                filename = os.path.basename(file)
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                if date_match:
                    available_dates.append(date_match.group(1))
            
            available_dates.sort(reverse=True)  # Most recent first
            
            return jsonify({
                'success': True,
                'connection_status': 'Local files available',
                'local_files_count': len(csv_files),
                'csv_files': [os.path.basename(f) for f in csv_files[:10]],  # Show first 10 files
                'available_dates': available_dates[:10],  # Show first 10 dates
                'latest_date': available_dates[0] if available_dates else None,
                'data_folder': DATA_FOLDER
            })
        else:
            return jsonify({
                'success': False,
                'error': f'No CSV files found in {DATA_FOLDER} folder'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Error checking local files: {str(e)}"
        })

@app.route('/get_available_dates')
def get_available_dates():
    """Get available dates from CSV files for datepicker highlighting"""
    try:
        csv_files = get_csv_files_from_folder()
        
        if csv_files:
            # Extract dates from filenames
            available_dates = []
            for file in csv_files:
                filename = os.path.basename(file)
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                if date_match:
                    available_dates.append(date_match.group(1))
            
            available_dates.sort(reverse=True)  # Most recent first
            
            return jsonify({
                'success': True,
                'available_dates': available_dates,
                'count': len(available_dates),
                'latest_date': available_dates[0] if available_dates else None
            })
        else:
            return jsonify({
                'success': False,
                'available_dates': [],
                'error': f'No CSV files found in {DATA_FOLDER} folder'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'available_dates': [],
            'error': f"Error getting available dates: {str(e)}"
        })

@app.route('/refresh_files')
def refresh_files():
    """Refresh the list of available local CSV files"""
    try:
        csv_files = get_csv_files_from_folder()
        
        if csv_files:
            # Extract dates and file info
            file_info = []
            for file_path in csv_files:
                filename = os.path.basename(file_path)
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                file_size = os.path.getsize(file_path)
                file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                file_info.append({
                    'filename': filename,
                    'date': date_match.group(1) if date_match else 'unknown',
                    'size_bytes': file_size,
                    'modified': file_modified.strftime("%Y-%m-%d %H:%M:%S")
                })
            
            return jsonify({
                'success': True,
                'total_files': len(csv_files),
                'files': file_info,
                'message': f"Found {len(csv_files)} CSV files in local folder"
            })
        else:
            return jsonify({
                'success': False,
                'total_files': 0,
                'files': [],
                'message': f"No CSV files found in {DATA_FOLDER} folder"
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Error refreshing files: {str(e)}"
        })

@app.route('/list_files')
def list_files():
    """List all CSV files in the local folder"""
    try:
        if os.path.exists(DATA_FOLDER):
            csv_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
            file_count = len(csv_files)
            
            # Sort files by name (which includes date)
            csv_files.sort(reverse=True)
            
            return jsonify({
                'success': True,
                'message': f"Found {file_count} CSV files in local folder.",
                'files': csv_files,
                'folder_path': os.path.abspath(DATA_FOLDER)
            })
        else:
            return jsonify({
                'success': False,
                'message': f"Data folder '{DATA_FOLDER}' does not exist.",
                'files': [],
                'folder_path': os.path.abspath(DATA_FOLDER)
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Error listing files: {str(e)}"
        })

def cleanup_on_exit():
    """Clean up function for graceful shutdown"""
    try:
        print(f"\nShutting down IBU Dashboard...")
        print("No temporary files to clean up (using local folder)")
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

@app.route('/get_latest_file_info')
def get_latest_file_info():
    """Get information about the latest CSV file for real-time updates"""
    try:
        file_path, date_str, file_timestamp = get_latest_csv_file()
        
        if not file_path or not date_str:
            return jsonify({
                "success": False,
                "message": "No CSV files found",
                "latest_file": "No data",
                "latest_date": "No data",
                "time_ago": "No recent data",
                "file_count": 0
            })
        
        # Format the information
        try:
            latest_file = os.path.basename(file_path)
            latest_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
            time_ago = get_time_ago_string(file_timestamp)
        except Exception:
            latest_file = os.path.basename(file_path) if file_path else "Unknown"
            latest_date = date_str
            time_ago = "Recently"
        
        # Get total file count
        csv_files = get_csv_files_from_folder()
        
        return jsonify({
            "success": True,
            "latest_file": latest_file,
            "latest_date": latest_date,
            "time_ago": time_ago,
            "file_count": len(csv_files),
            "file_path": file_path,
            "date_str": date_str
        })
        
    except Exception as e:
        print(f"Error getting latest file info: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Error retrieving file information"
        })

@app.route('/get_updates')
def get_updates():
    """Read update history from updates.txt file"""
    try:
        updates_file = os.path.join('static', 'updates.txt')
        
        if not os.path.exists(updates_file):
            return jsonify({
                "success": False,
                "error": "Updates file not found",
                "updates": []
            })
        
        updates = []
        
        with open(updates_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            try:
                # Parse format: VERSION|DATE|TITLE|FEATURES (semicolon separated)
                parts = line.split('|')
                if len(parts) >= 4:
                    version = parts[0].strip()
                    date = parts[1].strip()
                    title = parts[2].strip()
                    features_text = parts[3].strip()
                    
                    # Split features by semicolon
                    features = [f.strip() for f in features_text.split(';') if f.strip()]
                    
                    update_item = {
                        "version": version,
                        "date": date,
                        "title": title,
                        "features": features,
                        "is_current": version.lower().startswith("current")
                    }
                    
                    updates.append(update_item)
                    
            except Exception as e:
                print(f"Error parsing update line '{line}': {e}")
                continue
        
        return jsonify({
            "success": True,
            "updates": updates
        })
        
    except Exception as e:
        print(f"Error reading updates file: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "updates": []
        })

def parse_joined_date(joined_date_str):
    """Parse the joined date string to datetime object"""
    try:
        # Handle format like "December 19th, 2023"
        # Remove ordinal suffixes (st, nd, rd, th)
        cleaned_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', joined_date_str)
        return datetime.strptime(cleaned_date, "%B %d, %Y")
    except Exception as e:
        print(f"Error parsing date '{joined_date_str}': {e}")
        return None

def get_member_probation_status():
    """Calculate probation status for all members"""
    try:
        # Get all CSV files to track progress over time
        csv_files = get_csv_files_from_folder()
        if not csv_files:
            return {"error": "No CSV files found"}
        
        # Get current date for calculations
        current_date = datetime.now()
        
        # Load the latest CSV to get current member list
        latest_file = csv_files[0]
        latest_df = pd.read_csv(latest_file)
        
        # Clean column names first
        latest_df.columns = latest_df.columns.str.strip()
        
        # Store original column names for debugging
        original_columns = list(latest_df.columns)
        print(f"Original columns in latest file: {original_columns}")
        
        # Apply standard renames but preserve other columns
        column_renames = {}
        if "name" in latest_df.columns:
            column_renames["name"] = "Member"
        if "points" in latest_df.columns:
            column_renames["points"] = "Points"
        
        if column_renames:
            latest_df = latest_df.rename(columns=column_renames)
        
        print(f"Columns after rename: {list(latest_df.columns)}")
        
        # Verify required columns exist
        if "Member" not in latest_df.columns or "Points" not in latest_df.columns:
            return {"error": f"Required columns (Member, Points) missing. Found columns: {list(latest_df.columns)}"}
        
        if "Joined Date" not in latest_df.columns:
            return {"error": f"Joined Date column missing. Found columns: {list(latest_df.columns)}. Please ensure your CSV files contain member join date information."}
        
        members_status = []
        
        for _, member_row in latest_df.iterrows():
            try:
                member_name = member_row['Member']
                joined_date_str = str(member_row['Joined Date']).strip('"')
                current_points = int(member_row['Points'])
                
                # Parse joined date
                joined_date = parse_joined_date(joined_date_str)
                if not joined_date:
                    continue
                
                # Calculate time since joining
                days_since_joined = (current_date - joined_date).days
                
                # Define probation milestones
                week_1_target = 250000  # 250k points
                month_1_target = 1000000  # 1M points  
                month_3_target = 3000000  # 3M points
                
                # Calculate milestone dates
                week_1_date = joined_date + timedelta(days=7)
                month_1_date = joined_date + timedelta(days=30)
                month_3_date = joined_date + timedelta(days=90)
                
                # Track points at each milestone - use None to indicate no data found
                week_1_points = None
                month_1_points = None
                month_3_points = current_points  # Current total
                
                # Go through historical data to find points at milestone dates
                for csv_file in reversed(csv_files):  # Start from oldest
                    try:
                        # Extract date from filename
                        filename = os.path.basename(csv_file)
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                        if not date_match:
                            continue
                        
                        file_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                        
                        # Skip files before the member joined
                        if file_date < joined_date:
                            continue
                        
                        # Load CSV and find member
                        df = pd.read_csv(csv_file)
                        
                        # Clean column names first
                        df.columns = df.columns.str.strip()
                        
                        # Apply standard renames but preserve other columns  
                        column_renames = {}
                        if "name" in df.columns:
                            column_renames["name"] = "Member"
                        if "points" in df.columns:
                            column_renames["points"] = "Points"
                        
                        if column_renames:
                            df = df.rename(columns=column_renames)
                        
                        # Skip if essential columns are missing
                        if "Member" not in df.columns or "Points" not in df.columns:
                            continue
                        
                        # Find member data
                        member_data = df[df['Member'] == member_name]
                        
                        if member_data.empty:
                            continue
                        
                        points_at_date = int(member_data.iloc[0]['Points'])
                        
                        # Record points at milestone dates (find closest date after milestone)
                        if file_date >= week_1_date and week_1_points is None:
                            week_1_points = points_at_date
                        if file_date >= month_1_date and month_1_points is None:
                            month_1_points = points_at_date
                            
                    except Exception as e:
                        continue
                
                # Calculate remaining points needed first
                week_1_remaining = max(0, week_1_target - current_points) if current_date < week_1_date else 0
                month_1_remaining = max(0, month_1_target - current_points) if current_date < month_1_date else 0
                month_3_remaining = max(0, month_3_target - current_points) if current_date < month_3_date else 0
                
                # Enhanced logic: check if milestone is passed
                # A milestone is passed if:
                # 1. The deadline has passed AND they had enough points at the deadline (historical data), OR
                # 2. They currently have enough points (early achievement), OR
                # 3. No historical data available but current points show achievement
                # A milestone is failed ONLY if we have historical data showing they didn't meet the target
                week_1_passed = None
                if current_date >= week_1_date:
                    # Deadline has passed
                    if week_1_points is not None:
                        # We have historical data - check if they met the target
                        week_1_passed = week_1_points >= week_1_target
                    else:
                        # No historical data - can't determine failure, check current achievement
                        week_1_passed = current_points >= week_1_target if current_points >= week_1_target else None
                else:
                    # Deadline hasn't passed - check if they already achieved it
                    week_1_passed = current_points >= week_1_target if current_points >= week_1_target else None
                
                month_1_passed = None
                if current_date >= month_1_date:
                    # Deadline has passed
                    if month_1_points is not None:
                        # We have historical data - check if they met the target
                        month_1_passed = month_1_points >= month_1_target
                    else:
                        # No historical data - can't determine failure, check current achievement
                        month_1_passed = current_points >= month_1_target if current_points >= month_1_target else None
                else:
                    # Deadline hasn't passed - check if they already achieved it
                    month_1_passed = current_points >= month_1_target if current_points >= month_1_target else None
                
                month_3_passed = None
                if current_date >= month_3_date:
                    # Deadline has passed - always use current points as we have that data
                    month_3_passed = month_3_points >= month_3_target
                else:
                    # Deadline hasn't passed - check if they already achieved it
                    month_3_passed = current_points >= month_3_target if current_points >= month_3_target else None
                
                # Determine overall probation status
                probation_status = "in_progress"
                
                # Check if they completed all probation (passed all 3 milestones)
                if week_1_passed == True and month_1_passed == True and month_3_passed == True:
                    probation_status = "passed"
                # Check if they failed any milestone (only if deadline has passed AND they failed)
                elif current_date >= month_3_date and month_3_passed == False:
                    probation_status = "failed"
                elif current_date >= month_1_date and month_1_passed == False:
                    probation_status = "failed"
                elif current_date >= week_1_date and week_1_passed == False:
                    probation_status = "failed"
                
                # Post-probation compliance tracking (only for members who passed probation)
                post_probation_status = None
                post_probation_periods = []
                
                if probation_status == "passed":
                    # Calculate post-probation periods (90-day intervals starting after probation ends)
                    probation_end_date = month_3_date  # Probation ends after 3 months
                    
                    # Check if enough time has passed to start post-probation tracking
                    if current_date >= probation_end_date:
                        # Calculate all 90-day periods since probation ended
                        period_start = probation_end_date
                        period_number = 1
                        
                        # Process all periods (completed and current active period)
                        # Process all periods (completed and current active period)
                        while period_start <= current_date:
                            period_end = period_start + timedelta(days=90)
                            is_current_period = current_date < period_end  # True if this is the ongoing period
                            
                            # Find points at start and end of this period
                            points_at_start = 0
                            points_at_end = 0
                            
                            # Look through historical data for points at period boundaries
                            # We need EXACT dates for both boundaries, not closest approximations
                            period_start_found = False
                            period_end_found = False
                            
                            # Debug: print period info for current calculations
                            print(f"Processing period {period_number} for {member_name}: {period_start.date()} to {period_end.date()}, current_period: {is_current_period}")
                            
                            for csv_file in csv_files:  # Check all files, not just reversed
                                try:
                                    filename = os.path.basename(csv_file)
                                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                                    if not date_match:
                                        continue
                                    
                                    file_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                                    
                                    # Check for EXACT match with period start date
                                    if file_date.date() == period_start.date() and not period_start_found:
                                        # Load CSV and find member for period start
                                        df = pd.read_csv(csv_file)
                                        df.columns = df.columns.str.strip()
                                        
                                        column_renames = {}
                                        if "name" in df.columns:
                                            column_renames["name"] = "Member"
                                        if "points" in df.columns:
                                            column_renames["points"] = "Points"
                                        
                                        if column_renames:
                                            df = df.rename(columns=column_renames)
                                        
                                        if "Member" not in df.columns or "Points" not in df.columns:
                                            continue
                                        
                                        member_data = df[df['Member'] == member_name]
                                        if not member_data.empty:
                                            points_at_start = int(member_data.iloc[0]['Points'])
                                            period_start_found = True
                                            print(f"Found period start data: {points_at_start} points on {file_date.date()}")
                                    
                                    # For current period, use current points instead of end date
                                    if is_current_period:
                                        # For ongoing period, use the latest available CSV file for current points
                                        # Since current_date might not have a CSV, use the latest file
                                        if csv_file == csv_files[0]:  # This is the latest/most recent file
                                            df = pd.read_csv(csv_file)
                                            df.columns = df.columns.str.strip()
                                            
                                            column_renames = {}
                                            if "name" in df.columns:
                                                column_renames["name"] = "Member"
                                            if "points" in df.columns:
                                                column_renames["points"] = "Points"
                                            
                                            if column_renames:
                                                df = df.rename(columns=column_renames)
                                            
                                            if "Member" not in df.columns or "Points" not in df.columns:
                                                continue
                                            
                                            member_data = df[df['Member'] == member_name]
                                            if not member_data.empty:
                                                points_at_end = int(member_data.iloc[0]['Points'])
                                                period_end_found = True
                                                print(f"Found current period end data: {points_at_end} points on {file_date.date()}")
                                    else:
                                        # Check for EXACT match with period end date (completed periods only)
                                        if file_date.date() == period_end.date() and not period_end_found:
                                            # Load CSV and find member for period end
                                            df = pd.read_csv(csv_file)
                                            df.columns = df.columns.str.strip()
                                            
                                            column_renames = {}
                                            if "name" in df.columns:
                                                column_renames["name"] = "Member"
                                            if "points" in df.columns:
                                                column_renames["points"] = "Points"
                                            
                                            if column_renames:
                                                df = df.rename(columns=column_renames)
                                            
                                            if "Member" not in df.columns or "Points" not in df.columns:
                                                continue
                                            
                                            member_data = df[df['Member'] == member_name]
                                            if not member_data.empty:
                                                points_at_end = int(member_data.iloc[0]['Points'])
                                                period_end_found = True
                                                print(f"Found period end data: {points_at_end} points on {file_date.date()}")
                                    
                                    # Stop searching if we found both boundary points
                                    if period_start_found and (period_end_found or is_current_period):
                                        break
                                        
                                except Exception as e:
                                    continue
                            
                            # Calculate points earned in this period - ONLY if we have EXACT boundary data
                            points_earned = 0
                            target_points = 3000000  # 3M points per 90-day period
                            
                            # Determine if this period was successful
                            # We REQUIRE exact data for BOTH boundaries to make any determination
                            period_status = "insufficient_data"
                            if period_start_found and period_end_found and points_at_start >= 0 and points_at_end >= 0:
                                # Ensure we calculate period points correctly
                                points_earned = max(0, points_at_end - points_at_start)
                                
                                # Debug output
                                print(f"Period calculation for {member_name}: start={points_at_start}, end={points_at_end}, earned={points_earned}")
                                
                                # Sanity check: points earned in 90 days shouldn't exceed reasonable limits
                                # If points_earned is unreasonably high, it suggests data corruption
                                max_reasonable_points = 50000000  # 50M points in 90 days as sanity check
                                if points_earned > max_reasonable_points:
                                    # Data appears corrupted, mark as insufficient
                                    print(f"WARNING: Unreasonably high points earned ({points_earned}), marking as insufficient data")
                                    period_status = "insufficient_data"
                                    points_earned = 0
                                elif is_current_period:
                                    # For current period, use time-based risk assessment (accounts for burst earning patterns)
                                    days_elapsed = max(1, (current_date - period_start).days)  # Ensure at least 1 day
                                    
                                    if days_elapsed > 0 and days_elapsed <= 90:
                                        if points_earned >= target_points:
                                            period_status = "compliant"  # Already achieved target
                                        elif days_elapsed >= 85 and points_earned < target_points:
                                            period_status = "at_risk"   # Close to deadline without target
                                        else:
                                            period_status = "on_track"  # Still have time for burst activity
                                    else:
                                        period_status = "just_started"
                                else:
                                    # For completed periods, simple check
                                    period_status = "compliant" if points_earned >= target_points else "non_compliant"
                            
                            # Store the period info with clear data availability indicators
                            period_info = {
                                "period_number": period_number,
                                "start_date": period_start.strftime("%Y-%m-%d"),
                                "end_date": period_end.strftime("%Y-%m-%d"),
                                "points_at_start": points_at_start if period_start_found else None,
                                "points_at_end": points_at_end if period_end_found else None,
                                "points_earned": points_earned if period_start_found and period_end_found else None,
                                "target_points": target_points,
                                "status": period_status,
                                "start_date_found": period_start_found,
                                "end_date_found": period_end_found,
                                "is_current_period": is_current_period
                            }
                            
                            # Add projection data for current period
                            if is_current_period and period_start_found and period_end_found and period_status != "insufficient_data":
                                days_elapsed = max(1, (current_date - period_start).days)  # Ensure at least 1 day
                                days_remaining = max(0, 90 - days_elapsed)
                                
                                # Additional validation
                                if days_elapsed > 0 and days_elapsed <= 90 and points_earned >= 0:
                                    daily_rate = points_earned / days_elapsed
                                    projected_total = daily_rate * 90
                                    remaining_needed = max(0, target_points - points_earned)
                                    daily_needed = remaining_needed / max(1, days_remaining) if days_remaining > 0 else 0
                                    
                                    period_info.update({
                                        "days_elapsed": days_elapsed,
                                        "days_remaining": days_remaining,
                                        "daily_rate": daily_rate,
                                        "projected_total": projected_total,
                                        "remaining_needed": remaining_needed,
                                        "daily_needed": daily_needed
                                    })
                            
                            post_probation_periods.append(period_info)
                            
                            # Move to next period (but break if current period is ongoing)
                            if is_current_period:
                                break
                            period_start = period_end
                            period_number += 1
                        
                        # Determine overall post-probation status and limit to 3 most recent periods
                        if post_probation_periods:
                            # Keep only the 3 most recent periods (latest periods have highest period_number)
                            post_probation_periods = post_probation_periods[-3:]
                            
                            # Check if we have sufficient data for evaluation
                            periods_with_data = [p for p in post_probation_periods if p["status"] != "insufficient_data"]
                            
                            # Separate current period from completed periods for status determination
                            current_periods = [p for p in periods_with_data if p.get("is_current_period", False)]
                            completed_periods = [p for p in periods_with_data if not p.get("is_current_period", False)]
                            
                            if len(periods_with_data) == 0:
                                # No periods have sufficient data
                                post_probation_status = "insufficient_data"
                            else:
                                # Check for any non-compliant completed periods
                                non_compliant_completed = [p for p in completed_periods if p["status"] == "non_compliant"]
                                
                                if non_compliant_completed:
                                    post_probation_status = "non_compliant"
                                elif current_periods:
                                    # Use current period status if no completed non-compliant periods
                                    current_status = current_periods[0]["status"]  # Latest current period
                                    if current_status == "compliant":
                                        post_probation_status = "compliant"
                                    elif current_status == "on_track":
                                        post_probation_status = "on_track"
                                    elif current_status == "at_risk":
                                        post_probation_status = "at_risk"
                                    else:
                                        post_probation_status = "in_progress"
                                elif completed_periods:
                                    # Only completed periods, all compliant
                                    post_probation_status = "compliant"
                                else:
                                    post_probation_status = "insufficient_data"
                        else:
                            post_probation_status = "insufficient_data"
                    else:
                        post_probation_status = "too_early"  # Not enough time passed since probation ended
                
                member_status = {
                    "name": member_name,
                    "joined_date": joined_date_str,
                    "joined_date_parsed": joined_date.strftime("%Y-%m-%d"),
                    "days_since_joined": days_since_joined,
                    "current_points": current_points,
                    "probation_status": probation_status,
                    "post_probation_status": post_probation_status,
                    "post_probation_periods": post_probation_periods,
                    "milestones": {
                        "week_1": {
                            "target": week_1_target,
                            "points_at_deadline": week_1_points,
                            "has_historical_data": week_1_points is not None,
                            "passed": week_1_passed,
                            "deadline": week_1_date.strftime("%Y-%m-%d"),
                            "remaining_points": week_1_remaining,
                            "days_left": max(0, (week_1_date - current_date).days) if current_date < week_1_date else 0
                        },
                        "month_1": {
                            "target": month_1_target,
                            "points_at_deadline": month_1_points,
                            "has_historical_data": month_1_points is not None,
                            "passed": month_1_passed,
                            "deadline": month_1_date.strftime("%Y-%m-%d"),
                            "remaining_points": month_1_remaining,
                            "days_left": max(0, (month_1_date - current_date).days) if current_date < month_1_date else 0
                        },
                        "month_3": {
                            "target": month_3_target,
                            "points_at_deadline": month_3_points,
                            "has_historical_data": True,  # Always true since we use current points
                            "passed": month_3_passed,
                            "deadline": month_3_date.strftime("%Y-%m-%d"),
                            "remaining_points": month_3_remaining,
                            "days_left": max(0, (month_3_date - current_date).days) if current_date < month_3_date else 0
                        }
                    }
                }
                
                members_status.append(member_status)
                
            except Exception as e:
                continue
        
        # Sort by probation status priority and days since joined
        status_priority = {"failed": 0, "in_progress": 1, "completed": 2}
        members_status.sort(key=lambda x: (status_priority.get(x["probation_status"], 1), x["days_since_joined"]))
        
        return {"success": True, "members": members_status}
        
    except Exception as e:
        print(f"Error calculating probation status: {str(e)}")
        return {"error": str(e)}

@app.route('/member_info')
def member_info():
    """Member info page with probation tracking"""
    try:
        # Get the latest file info for the header
        file_path, date_str, file_timestamp = get_latest_csv_file()
        
        if file_path:
            latest_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y") if date_str else "Unknown"
            time_ago = get_time_ago_string(file_timestamp)
        else:
            latest_date = "No data"
            time_ago = "Unknown"
        
        return render_template('member_info.html', 
                             latest_date=latest_date, 
                             time_ago=time_ago)
        
    except Exception as e:
        print(f"Error in member_info route: {str(e)}")
        return render_template('member_info.html', 
                             latest_date="Error", 
                             time_ago="Error")

@app.route('/get_probation_data')
def get_probation_data():
    """API endpoint to get probation status data"""
    try:
        probation_data = get_member_probation_status()
        
        # Check for probation failures and send notifications
        if NOTIFICATIONS_ENABLED and probation_data and 'members' in probation_data:
            try:
                # Get the current CSV file for notification tracking
                file_path, _, _ = get_latest_csv_file()
                notification_service.check_and_notify_failures(probation_data['members'], file_path)
            except Exception as e:
                print(f"Error sending notifications: {e}")
                # Don't fail the API call if notifications fail
        
        return jsonify(probation_data)
    except Exception as e:
        print(f"Error in get_probation_data: {str(e)}")
        return jsonify({"error": str(e)})

@app.route('/test_notification')
def test_notification():
    """Test endpoint to send a sample probation failure notification - requires authentication"""
    # Check if user is authenticated
    if not session.get('admin_authenticated'):
        return jsonify({"error": "Authentication required"}), 401
    
    if not NOTIFICATIONS_ENABLED:
        return jsonify({"error": "Notifications not enabled. Check notification_service.py import and email configuration."})
    
    try:
        # Create a test member data
        test_member = {
            "name": "Test Member",
            "joined_date": "2025-01-01",
            "days_since_joined": 100,
            "current_points": 250000,
            "probation_status": "failed",
            "milestones": {
                "week_1": {
                    "target": 500000,
                    "passed": False,
                    "points_at_deadline": 100000,
                    "remaining_points": 400000,
                    "days_left": 0
                },
                "month_1": {
                    "target": 1500000,
                    "passed": False,
                    "points_at_deadline": 250000,
                    "remaining_points": 1250000,
                    "days_left": 0
                },
                "month_3": {
                    "target": 3000000,
                    "passed": None,
                    "points_at_deadline": None,
                    "remaining_points": 2750000,
                    "days_left": 10
                }
            }
        }
        
        # Send test notification
        success = notification_service.notify_probation_failure(test_member)
        
        if success:
            return jsonify({"message": "Test notification sent successfully!"})
        else:
            return jsonify({"error": "Failed to send test notification. Check email configuration."})
            
    except Exception as e:
        return jsonify({"error": f"Error sending test notification: {str(e)}"})

@app.route('/notification_admin')
def notification_admin():
    """Admin panel for notification system - requires authentication"""
    # Check if user is authenticated
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))
    
    return render_template('notification_admin.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            return redirect(url_for('notification_admin'))
        else:
            return render_template('admin_login.html', error='Invalid password')
    
    return render_template('admin_login.html')

@app.route('/admin_logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    return redirect(url_for('admin_login'))

@app.route('/notification_status')
def notification_status():
    """Get notification system status and configuration - requires authentication"""
    # Check if user is authenticated
    if not session.get('admin_authenticated'):
        return jsonify({"error": "Authentication required"}), 401
    
    if not NOTIFICATIONS_ENABLED:
        return jsonify({
            "enabled": False,
            "error": "Notification service not available"
        })
    
    try:
        config_status = {
            "enabled": True,
            "smtp_server": notification_service.smtp_server,
            "smtp_port": notification_service.smtp_port,
            "sender_email": notification_service.sender_email or "Not configured",
            "sender_configured": bool(notification_service.sender_email),
            "admin_emails_configured": len(notification_service.admin_emails),
            "admin_emails": notification_service.admin_emails if notification_service.admin_emails else [],
            "notification_history_count": len(notification_service.notification_history)
        }
        return jsonify(config_status)
    except Exception as e:
        return jsonify({
            "enabled": False,
            "error": str(e)
        })

@app.route('/api/file_count')
def get_file_count():
    """Get count of CSV files available in the specified date range"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({"error": "Both start_date and end_date are required"}), 400
        
        # Parse dates
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        if start_dt > end_dt:
            return jsonify({"error": "Start date cannot be after end date"}), 400
        
        # Check if the data folder exists
        if not os.path.exists(DATA_FOLDER):
            return jsonify({"error": "Data folder not found"}), 404
        
        # Get all CSV files in the data folder
        csv_files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))
        
        # Filter files based on date range
        filtered_files = []
        for csv_file in csv_files:
            filename = os.path.basename(csv_file)
            # Extract date from filename (format: sheepit_team_points_YYYY-MM-DD.csv)
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
            if date_match:
                file_date_str = date_match.group(1)
                try:
                    file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                    if start_dt <= file_date <= end_dt:
                        filtered_files.append(csv_file)
                except ValueError:
                    continue
        
        return jsonify({
            "file_count": len(filtered_files),
            "total_files": len(csv_files)
        })
        
    except Exception as e:
        print(f"Error getting file count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/download_csv_files')
def download_csv_files():
    """Download CSV files from the Scraped_Team_Info folder as a ZIP archive with optional date filtering"""
    try:
        # Get date range parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Check if the data folder exists
        if not os.path.exists(DATA_FOLDER):
            return jsonify({"error": "Data folder not found"}), 404
        
        # Get all CSV files in the data folder
        csv_files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))
        
        if not csv_files:
            return jsonify({"error": "No CSV files found in data folder"}), 404
        
        # Filter files based on date range if provided
        filtered_files = csv_files
        if start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                
                filtered_files = []
                for csv_file in csv_files:
                    filename = os.path.basename(csv_file)
                    # Extract date from filename (format: sheepit_team_points_YYYY-MM-DD.csv)
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                    if date_match:
                        file_date_str = date_match.group(1)
                        try:
                            file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                            if start_dt <= file_date <= end_dt:
                                filtered_files.append(csv_file)
                        except ValueError:
                            continue
                
                if not filtered_files:
                    return jsonify({"error": "No CSV files found in the specified date range"}), 404
                    
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        # Create a ZIP file in memory
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for csv_file in filtered_files:
                # Get just the filename (not the full path)
                filename = os.path.basename(csv_file)
                # Add file to ZIP
                zf.write(csv_file, filename)
        
        memory_file.seek(0)
        
        # Generate filename based on date range or timestamp
        if start_date and end_date:
            start_formatted = start_date.replace('-', '')
            end_formatted = end_date.replace('-', '')
            zip_filename = f"IBU_Team_Data_{start_formatted}_to_{end_formatted}.zip"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"IBU_Team_Data_{timestamp}.zip"
        
        return send_file(
            memory_file,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        print(f"Error creating CSV download: {str(e)}")
        return jsonify({"error": f"Failed to create download: {str(e)}"}), 500

# Flask startup
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))  # Render provides PORT env var
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    print("Starting IBU Dashboard...")
    print(f"Access the dashboard at: http://localhost:{port}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)