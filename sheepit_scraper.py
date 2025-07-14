import requests
from bs4 import BeautifulSoup
import csv
import os
from datetime import datetime
import hashlib

# Configuration
SCRAPED_TEAM_INFO_FOLDER = "Scraped_Team_Info"

# SheepIt URLs
LOGIN_URL = "https://www.sheepit-renderfarm.com/user/authenticate"
TEAM_URL = "https://www.sheepit-renderfarm.com/team/2109"

# Login credentials - You'll need to set these as environment variables or modify as needed
USERNAME = "Data_Seeker"
PASSWORD = "data_seeker_42"

def name_to_color(name):
    """Generate a consistent color for a team member name"""
    hash_object = hashlib.md5(name.encode())
    return "#" + hash_object.hexdigest()[:6]

def ensure_output_folder():
    """Create the output folder if it doesn't exist"""
    if not os.path.exists(SCRAPED_TEAM_INFO_FOLDER):
        os.makedirs(SCRAPED_TEAM_INFO_FOLDER)
        print(f"Created folder: {SCRAPED_TEAM_INFO_FOLDER}")

def scrape_team_data():
    """Scrape team data from SheepIt renderfarm"""
    print("🔄 Starting SheepIt team data scraping...")
    
    # Login payload
    payload = {
        "login": USERNAME,
        "password": PASSWORD,
    }
    
    try:
        # Start session and login
        print("🔑 Logging into SheepIt...")
        with requests.session() as session:
            login_response = session.post(LOGIN_URL, data=payload)
            
            if login_response.status_code != 200:
                print(f"❌ Login failed with status code: {login_response.status_code}")
                return None
            
            # Get team page
            print("📊 Fetching team data...")
            team_response = session.get(TEAM_URL)
            
            if team_response.status_code != 200:
                print(f"❌ Failed to get team page. Status code: {team_response.status_code}")
                return None
            
            # Parse HTML
            soup = BeautifulSoup(team_response.content, "html.parser")
            table = soup.find("table")
            
            if not table:
                print("❌ Could not find team table on the page.")
                return None
            
            # Extract data from table
            rows = table.find_all("tr")[1:]  # Skip header
            team_data = []
            
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue
                    
                rank = cols[0].get_text(strip=True)
                member_name = cols[1].get_text(strip=True)
                points_text = cols[2].get_text(strip=True).replace(",", "")
                joined_date_text = cols[3].get_text(strip=True)
                color = name_to_color(member_name)
                
                try:
                    points = int(points_text)
                except ValueError:
                    points = 0
                    
                team_data.append({
                    "rank": rank,
                    "name": member_name,
                    "points": points,
                    "joined_date": joined_date_text,
                    "color": color
                })
            
            print(f"✅ Successfully scraped data for {len(team_data)} team members")
            return team_data
            
    except requests.RequestException as e:
        print(f"❌ Network error during scraping: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error during scraping: {e}")
        return None

def save_team_data_to_csv(team_data):
    """Save team data to CSV file in the Scraped_Team_Info folder"""
    if not team_data:
        print("❌ No team data to save")
        return None
    
    # Ensure output folder exists
    ensure_output_folder()
    
    # Generate filename with current date
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d")
    csv_filename = f"sheepit_team_points_{timestamp_str}.csv"
    csv_filepath = os.path.join(SCRAPED_TEAM_INFO_FOLDER, csv_filename)
    
    try:
        # Write CSV file
        print(f"💾 Saving data to: {csv_filepath}")
        with open(csv_filepath, 'w', newline='', encoding='utf-8') as csvfile:
            # Use simplified headers that match the dashboard expectations
            writer = csv.writer(csvfile)
            writer.writerow(["name", "points"])  # Simple format for dashboard compatibility
            
            for entry in team_data:
                writer.writerow([entry["name"], entry["points"]])
        
        print(f"✅ Successfully saved {len(team_data)} records to {csv_filename}")
        return csv_filepath
        
    except Exception as e:
        print(f"❌ Error saving CSV file: {e}")
        return None

def main():
    """Main function to run the scraper"""
    print("🚀 SheepIt Team Data Scraper - Local Version")
    print("=" * 50)
    
    # Check credentials
    if USERNAME == "your_username_here" or PASSWORD == "your_password_here":
        print("⚠️  WARNING: Please set your SheepIt credentials!")
        print("You can either:")
        print("1. Set environment variables: SHEEPIT_USERNAME and SHEEPIT_PASSWORD")
        print("2. Edit this script and replace the placeholder values")
        print("\nExample using environment variables:")
        print("Windows: set SHEEPIT_USERNAME=your_username && set SHEEPIT_PASSWORD=your_password")
        print("Linux/Mac: export SHEEPIT_USERNAME=your_username && export SHEEPIT_PASSWORD=your_password")
        return
    
    # Scrape team data
    team_data = scrape_team_data()
    
    if team_data:
        # Save to CSV
        csv_path = save_team_data_to_csv(team_data)
        
        if csv_path:
            print("=" * 50)
            print("🎉 Scraping completed successfully!")
            print(f"📁 File saved: {csv_path}")
            print(f"📊 Records: {len(team_data)} team members")
            print("\n💡 The dashboard will automatically detect this new file within 30 seconds!")
        else:
            print("❌ Failed to save CSV file")
    else:
        print("❌ Failed to scrape team data")

if __name__ == "__main__":
    main()
