from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import io
import os
from datetime import datetime, timedelta
from googleapiclient.http import MediaIoBaseDownload
from load_credentials import load_credentials

# Scopes for Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
PARENT_FOLDER_ID = "19v2po0tDgQf8a_qeKsmPOqole_5BIN5_"  # Google Drive folder ID
DATA_FOLDER = "Scraped_Team_Info"  # Local folder to save downloaded files

# Global variables for lazy loading
credentials = None
drive_service = None

def authenticate_drive_api():
    """Authenticate and return Google Drive service using service account credentials"""
    global credentials, drive_service
    if credentials is None:
        from load_credentials import load_credentials
        credentials = load_credentials(SCOPES)
    if drive_service is None:
        drive_service = build('drive', 'v3', credentials=credentials)
    return drive_service

def ensure_data_folder():
    """Ensure the data folder exists"""
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

def list_csv_files(folder_id=None):
    """List all CSV files in the Google Drive folder"""
    if folder_id is None:
        folder_id = PARENT_FOLDER_ID
    
    drive_service = authenticate_drive_api()
    # Look for CSV files that contain the team points pattern
    query = f"'{folder_id}' in parents and name contains 'sheepit_team_points_' and mimeType='text/csv'"
    results = drive_service.files().list(q=query, pageSize=100, fields="files(id,name,mimeType)").execute()
    files = results.get('files', [])
    return files

def get_available_dates():
    """Get list of available dates from Google Drive files"""
    files = list_csv_files()
    dates = []
    for file in files:
        # Extract date from filename: sheepit_team_points_YYYY-MM-DD.csv or sheepit_team_points_YYYY-MM-DD
        name = file['name']
        if 'sheepit_team_points_' in name:
            try:
                # Remove prefix and any file extension
                date_str = name.replace('sheepit_team_points_', '')
                date_str = date_str.replace('.csv', '')
                # Validate that it's a proper date format
                datetime.strptime(date_str, '%Y-%m-%d')
                dates.append(date_str)
            except:
                continue
    return sorted(dates, reverse=True)  # Most recent first

def download_file(file_id, destination):
    """Download a CSV file from Google Drive"""
    ensure_data_folder()
    drive_service = authenticate_drive_api()
    
    # Download CSV file using get_media
    request = drive_service.files().get_media(fileId=file_id)
    
    fh = io.FileIO(destination, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.close()
    return True

def find_file_by_date(target_date):
    """Find a specific file by date"""
    files = list_csv_files()
    for file in files:
        if f'sheepit_team_points_{target_date}' in file['name']:
            return file
    return None

def download_file_by_date(target_date):
    """Download a specific file by date"""
    file_info = find_file_by_date(target_date)
    if not file_info:
        return None, f"File for date {target_date} not found in Google Drive"
    
    filename = f"sheepit_team_points_{target_date}.csv"
    local_path = os.path.join(DATA_FOLDER, filename)
    
    # Check if file already exists locally
    if os.path.exists(local_path):
        return local_path, f"File already exists locally: {local_path}"
    
    try:
        download_file(file_info['id'], local_path)
        return local_path, f"Successfully downloaded: {filename}"
    except Exception as e:
        return None, f"Error downloading file: {str(e)}"

def download_files_for_date_range(start_date, end_date):
    """Download files for a date range"""
    available_dates = get_available_dates()
    requested_dates = []
    
    # Generate list of dates in range
    from datetime import datetime, timedelta
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    current = start
    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        if date_str in available_dates:
            requested_dates.append(date_str)
        current += timedelta(days=1)
    
    results = []
    for date in requested_dates:
        path, message = download_file_by_date(date)
        results.append({
            'date': date,
            'path': path,
            'message': message,
            'success': path is not None
        })
    
    return results

def sync_latest_files(days_back=7):
    """Sync the latest files from Google Drive"""
    from datetime import datetime, timedelta
    
    today = datetime.today().date()
    start_date = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    return download_files_for_date_range(start_date, end_date)

def check_file_exists_locally(date):
    """Check if a file exists locally"""
    filename = f"sheepit_team_points_{date}.csv"
    local_path = os.path.join(DATA_FOLDER, filename)
    return os.path.exists(local_path), local_path

def get_file_path(date):
    """Get the local path for a file, downloading if necessary"""
    exists, local_path = check_file_exists_locally(date)
    if exists:
        return local_path, f"File already available locally: {local_path}"
    
    # File doesn't exist locally, try to download
    return download_file_by_date(date)

# ===== INTERFACE FUNCTIONS FOR IBU_SCRAPER INTEGRATION =====

def ensure_files_available(file_requests):
    """
    Main interface function for IBU_scraper.py
    
    Args:
        file_requests: List of file requests, each containing:
            - type: 'single_date', 'date_range', 'latest', or 'latest_n_days'
            - date: specific date (for single_date)
            - start_date: start date (for date_range)
            - end_date: end date (for date_range)
            - days_back: number of days back (for latest_n_days)
    
    Returns:
        Dictionary with:
            - success: boolean
            - files: list of downloaded file paths
            - messages: list of status messages
            - errors: list of any errors encountered
    """
    results = {
        'success': True,
        'files': [],
        'messages': [],
        'errors': []
    }
    
    for request in file_requests:
        try:
            if request['type'] == 'single_date':
                path, message = get_file_path(request['date'])
                if path:
                    results['files'].append(path)
                    results['messages'].append(message)
                else:
                    results['errors'].append(message)
                    results['success'] = False
                    
            elif request['type'] == 'date_range':
                range_results = download_files_for_date_range(
                    request['start_date'], 
                    request['end_date']
                )
                for result in range_results:
                    if result['success']:
                        results['files'].append(result['path'])
                        results['messages'].append(result['message'])
                    else:
                        results['errors'].append(result['message'])
                        results['success'] = False
                        
            elif request['type'] == 'latest':
                available_dates = get_available_dates()
                if available_dates:
                    latest_date = available_dates[0]
                    path, message = get_file_path(latest_date)
                    if path:
                        results['files'].append(path)
                        results['messages'].append(message)
                    else:
                        results['errors'].append(message)
                        results['success'] = False
                else:
                    results['errors'].append("No files available in Google Drive")
                    results['success'] = False
                    
            elif request['type'] == 'latest_n_days':
                sync_results = sync_latest_files(request.get('days_back', 7))
                for result in sync_results:
                    if result['success']:
                        results['files'].append(result['path'])
                        results['messages'].append(result['message'])
                    else:
                        results['errors'].append(result['message'])
                        
        except Exception as e:
            error_msg = f"Error processing request {request}: {str(e)}"
            results['errors'].append(error_msg)
            results['success'] = False
    
    return results

def get_latest_file_path():
    """Get the path to the latest available file, downloading if necessary"""
    available_dates = get_available_dates()
    if not available_dates:
        return None, "No files available in Google Drive", None
    
    latest_date = available_dates[0]
    file_path, message = get_file_path(latest_date)
    
    # Get the Google Drive timestamp for the latest file
    file_timestamp = None
    if file_path:
        try:
            file_timestamp = get_google_drive_file_timestamp(latest_date)
        except Exception as e:
            print(f"Warning: Could not get timestamp for {latest_date}: {e}")
    
    return file_path, message, file_timestamp

def get_google_drive_file_timestamp(date_str):
    """Get the creation/modification timestamp from Google Drive for a specific file"""
    try:
        drive_service = authenticate_drive_api()
        
        # Find the file by name pattern
        filename_pattern = f"sheepit_team_points_{date_str}"
        query = f"'{PARENT_FOLDER_ID}' in parents and name contains '{filename_pattern}' and mimeType='text/csv'"
        
        results = drive_service.files().list(
            q=query, 
            pageSize=10, 
            fields="files(id,name,createdTime,modifiedTime)"
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            # Get the first matching file
            file_info = files[0]
            
            # Use modifiedTime if available, otherwise createdTime
            timestamp_str = file_info.get('modifiedTime') or file_info.get('createdTime')
            
            if timestamp_str:
                # Parse ISO format timestamp (e.g., "2025-07-03T14:30:25.123Z")
                from datetime import datetime
                # Remove the 'Z' and parse
                timestamp_str = timestamp_str.replace('Z', '+00:00')
                file_timestamp = datetime.fromisoformat(timestamp_str)
                
                # Convert to local time (remove timezone info for simplicity)
                file_timestamp = file_timestamp.replace(tzinfo=None)
                
                return file_timestamp
        
        return None
        
    except Exception as e:
        print(f"Error getting Google Drive timestamp: {e}")
        return None

def get_files_for_week_range(start_date, end_date):
    """Get files for a specific week range"""
    return download_files_for_date_range(start_date, end_date)

def get_files_for_month_range(start_date, end_date):
    """Get files for a specific month range"""
    return download_files_for_date_range(start_date, end_date)

def get_files_for_year_range(start_date, end_date):
    """Get files for a specific year range"""
    return download_files_for_date_range(start_date, end_date)

def validate_file_exists_and_download(date):
    """
    Validate if a file exists locally or in Google Drive and download if necessary
    Returns: (file_path, success, message)
    """
    # Check if file exists locally first
    exists_locally, local_path = check_file_exists_locally(date)
    if exists_locally:
        return local_path, True, f"File already available locally: {local_path}"
    
    # Try to download from Google Drive
    path, message = download_file_by_date(date)
    if path:
        return path, True, message
    else:
        return None, False, message

def get_missing_files_for_range(start_date, end_date):
    """
    Get list of missing files for a date range
    Returns list of dates that are missing both locally and in Google Drive
    """
    from datetime import datetime, timedelta
    
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    available_dates = get_available_dates()
    
    missing_dates = []
    current = start
    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        exists_locally, _ = check_file_exists_locally(date_str)
        if not exists_locally and date_str not in available_dates:
            missing_dates.append(date_str)
        current += timedelta(days=1)
    
    return missing_dates

# ===== TEST AND UTILITY FUNCTIONS =====

def test_drive_connection():
    """Test the connection to Google Drive by checking folder access"""
    try:
        drive_service = authenticate_drive_api()
        
        # Simple folder access test - just check if we can query the folder
        query = f"'{PARENT_FOLDER_ID}' in parents"
        results = drive_service.files().list(q=query, pageSize=1, fields="files(id,name)").execute()
        
        # If we can execute the query without error, connection is working
        files = results.get('files', [])
        return True, f"Successfully connected to Google Drive. Folder accessible."
        
    except Exception as e:
        return False, f"Failed to connect to Google Drive: {str(e)}"

def list_all_available_files():
    """List all available files in Google Drive and locally"""
    drive_files = list_csv_files()
    local_files = []
    
    if os.path.exists(DATA_FOLDER):
        for file in os.listdir(DATA_FOLDER):
            if file.startswith("sheepit_team_points_") and file.endswith(".csv"):
                local_files.append(file)
    
    return {
        'drive_files': [f['name'] for f in drive_files],
        'local_files': local_files,
        'drive_count': len(drive_files),
        'local_count': len(local_files)
    }

def cleanup_old_files(days_to_keep=30):
    """Remove local files older than specified days"""
    from datetime import datetime, timedelta
    
    if not os.path.exists(DATA_FOLDER):
        return []
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    removed_files = []
    
    for file in os.listdir(DATA_FOLDER):
        if file.startswith("sheepit_team_points_") and file.endswith(".csv"):
            file_path = os.path.join(DATA_FOLDER, file)
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if file_mod_time < cutoff_date:
                os.remove(file_path)
                removed_files.append(file)
    
    return removed_files

if __name__ == "__main__":
    # Test the connection when run directly
    print("Testing Google Drive connection...")
    success, message = test_drive_connection()
    print(f"Status: {message}")
    
    if success:
        print("\nListing available files...")
        file_info = list_all_available_files()
        print(f"Drive files: {file_info['drive_count']}")
        print(f"Local files: {file_info['local_count']}")
        
        print("\nAvailable dates:", get_available_dates()[:5])  # Show first 5 dates
