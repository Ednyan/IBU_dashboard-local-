from flask import Flask, request, render_template, jsonify, Response
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

# Flask startup
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))  # Render provides PORT env var
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    print("Starting IBU Dashboard...")
    print(f"Access the dashboard at: http://localhost:{port}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)