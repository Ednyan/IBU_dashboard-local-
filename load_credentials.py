import os
import json
from google.oauth2 import service_account

def load_credentials(scopes):
    """
    Load Google Service Account credentials from environment variables or JSON file.
    Priority: Environment variables > service_account.json file
    """
    
    # Try to load from environment variables first (SECURE)
    service_account_key = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY')
    
    if service_account_key:
        try:
            # Parse the JSON string from environment variable
            service_account_info = json.loads(service_account_key)
            print("✅ Loading credentials from environment variables (SECURE)")
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=scopes
            )
            return credentials
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing GOOGLE_SERVICE_ACCOUNT_KEY: {e}")
            print("Falling back to service_account.json file...")
    
    # Fallback to JSON file (DEVELOPMENT ONLY)
    json_file_path = "service_account.json"
    if os.path.exists(json_file_path):
        print("⚠️  Loading credentials from service_account.json (DEVELOPMENT ONLY)")
        print("⚠️  WARNING: For production, use GOOGLE_SERVICE_ACCOUNT_KEY environment variable!")
        
        with open(json_file_path, "r") as f:
            service_account_info = json.load(f)
        
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=scopes
        )
        return credentials
    
    # No credentials found
    raise ValueError(
        "❌ No Google Service Account credentials found!\n"
        "Either:\n"
        "1. Set GOOGLE_SERVICE_ACCOUNT_KEY environment variable with JSON content, OR\n"
        "2. Place service_account.json file in the project directory"
    )