#!/usr/bin/env python3
"""
Helper script to convert service_account.json to environment variable format
"""
import json
import os
import sys

def main():
    print("🔒 Service Account to Environment Variable Converter")
    print("=" * 50)
    
    # Check if service_account.json exists
    if not os.path.exists("service_account.json"):
        print("❌ service_account.json not found in current directory!")
        print("Please make sure the file exists and try again.")
        return
    
    try:
        # Read the service account file
        with open("service_account.json", "r") as f:
            service_account_data = json.load(f)
        
        # Convert to single-line JSON string
        env_var_value = json.dumps(service_account_data, separators=(',', ':'))
        
        print("✅ Successfully converted service_account.json!")
        print("\n📋 COPY THIS VALUE FOR YOUR ENVIRONMENT VARIABLE:")
        print("=" * 60)
        print("Variable Name: GOOGLE_SERVICE_ACCOUNT_KEY")
        print("Variable Value:")
        print(env_var_value)
        print("=" * 60)
        
        # Save to a temp file for easy copying
        with open("env_var_temp.txt", "w") as f:
            f.write(f"GOOGLE_SERVICE_ACCOUNT_KEY={env_var_value}")
        
        print(f"\n💾 Also saved to 'env_var_temp.txt' for easy copying")
        print("⚠️  Remember to delete 'env_var_temp.txt' after use!")
        
        print("\n🚀 Next Steps:")
        print("1. Copy the value above")
        print("2. Set it as GOOGLE_SERVICE_ACCOUNT_KEY in your deployment platform")
        print("3. Remove service_account.json from your repository")
        print("4. Delete the env_var_temp.txt file")
        
    except json.JSONDecodeError as e:
        print(f"❌ Error reading service_account.json: {e}")
        print("Please check that the file contains valid JSON.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
