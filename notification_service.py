import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import json
from typing import List, Dict, Optional

class NotificationService:
    """
    Service for sending email notifications about member probation status changes
    """
    
    def __init__(self):
        # Email configuration - you can set these as environment variables
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        
        # Recipients configuration
        self.admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
        self.admin_emails = [email.strip() for email in self.admin_emails if email.strip()]
        
        # Notification settings
        self.notifications_file = "notification_history.json"
        self.notification_history = self.load_notification_history()
        
        # CSV tracking to prevent duplicate notifications
        self.last_processed_csv = self.notification_history.get('last_processed_csv', '')
        self.last_notification_date = self.notification_history.get('last_notification_date', '')
        
    def load_notification_history(self) -> Dict:
        """Load notification history to avoid duplicate notifications"""
        try:
            if os.path.exists(self.notifications_file):
                with open(self.notifications_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading notification history: {e}")
        return {}
    
    def save_notification_history(self):
        """Save notification history"""
        try:
            # Update tracking info before saving
            self.notification_history['last_processed_csv'] = self.last_processed_csv
            self.notification_history['last_notification_date'] = self.last_notification_date
            
            with open(self.notifications_file, 'w') as f:
                json.dump(self.notification_history, f, indent=2)
        except Exception as e:
            print(f"Error saving notification history: {e}")
    
    def should_check_for_notifications(self, current_csv_file: str) -> bool:
        """
        Determine if we should check for notifications based on CSV file and date
        Only check if:
        1. New CSV file detected, OR
        2. Same CSV but different day (in case CSV is updated)
        """
        from datetime import datetime
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Extract just the filename from the full path for comparison
        current_csv_name = os.path.basename(current_csv_file) if current_csv_file else ''
        last_csv_name = os.path.basename(self.last_processed_csv) if self.last_processed_csv else ''
        
        # Check if this is a new CSV file or a new day
        if current_csv_name != last_csv_name:
            print(f"📊 New CSV detected: {current_csv_name} (previous: {last_csv_name})")
            return True
        elif current_date != self.last_notification_date:
            print(f"📅 Same CSV but new day: {current_date} (last notification: {self.last_notification_date})")
            return True
        
        print(f"⏭️ Skipping notification check - already processed {current_csv_name} today ({current_date})")
        return False
    
    def update_csv_tracking(self, csv_file: str):
        """Update the tracking info for the last processed CSV"""
        from datetime import datetime
        
        self.last_processed_csv = csv_file
        self.last_notification_date = datetime.now().strftime('%Y-%m-%d')
        self.save_notification_history()
        
        print(f"📝 Updated CSV tracking: {os.path.basename(csv_file)} on {self.last_notification_date}")
    
    def has_been_notified(self, member_name: str, status: str) -> bool:
        """Check if we've already sent a notification for this member and status"""
        key = f"{member_name}_{status}"
        return key in self.notification_history
    
    def mark_as_notified(self, member_name: str, status: str):
        """Mark that we've sent a notification for this member and status"""
        key = f"{member_name}_{status}"
        self.notification_history[key] = {
            "timestamp": datetime.now().isoformat(),
            "member": member_name,
            "status": status
        }
        self.save_notification_history()
    
    def create_failure_email(self, member_data: Dict) -> tuple:
        """Create email content for probation failure notification"""
        subject = f"🚨 PROBATION FAILURE ALERT: {member_data.get('name', 'Unknown Member')}"
        
        # Safely get member data with defaults
        member_name = member_data.get('name', 'Unknown Member')
        joined_date = member_data.get('joined_date', 'Unknown')
        days_since_joined = member_data.get('days_since_joined', 'Unknown')
        current_points = member_data.get('current_points', 0)
        
        # Ensure current_points is a number for formatting
        if current_points is None:
            current_points = 0
        
        # Determine which milestone(s) failed
        failed_milestones = []
        milestones = member_data.get('milestones', {})
        
        if milestones.get('week_1', {}).get('passed') == False:
            failed_milestones.append("First Week (500K points)")
        if milestones.get('month_1', {}).get('passed') == False:
            failed_milestones.append("First Month (1.5M points)")
        if milestones.get('month_3', {}).get('passed') == False:
            failed_milestones.append("Three Months (3M points)")
        
        failed_text = ", ".join(failed_milestones) if failed_milestones else "Unknown milestone"
        
        # Create HTML email content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #e06150, #d14a3a); color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ padding: 20px; }}
                .alert {{ background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin: 15px 0; border-radius: 4px; }}
                .details {{ background-color: #f9fafb; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                .milestone {{ padding: 10px; margin: 5px 0; border-radius: 6px; }}
                .milestone.failed {{ background-color: #fef2f2; border-left: 3px solid #ef4444; }}
                .milestone.passed {{ background-color: #f0fdf4; border-left: 3px solid #22c55e; }}
                .milestone.pending {{ background-color: #fefce8; border-left: 3px solid #eab308; }}
                .footer {{ background-color: #f9fafb; padding: 15px; border-radius: 0 0 10px 10px; text-align: center; font-size: 12px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Probation Failure Alert</h1>
                    <p>Immediate attention required</p>
                </div>
                
                <div class="content">
                    <div class="alert">
                        <h2>Member: {member_name}</h2>
                        <p><strong>Status:</strong> FAILED PROBATION</p>
                        <p><strong>Failed Milestone(s):</strong> {failed_text}</p>
                    </div>
                    
                    <div class="details">
                        <h3>Member Details</h3>
                        <p><strong>Joined Date:</strong> {joined_date}</p>
                        <p><strong>Days Since Joining:</strong> {days_since_joined}</p>
                        <p><strong>Current Points:</strong> {current_points:,}</p>
                        <p><strong>Notification Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    
                    <h3>Milestone Status</h3>
        """
        
        # Add milestone details
        milestone_order = [
            ('week_1', 'First Week', '500K points'),
            ('month_1', 'First Month', '1.5M points'),
            ('month_3', 'Three Months', '3M points')
        ]
        
        for key, title, target in milestone_order:
            milestone = milestones.get(key, {})
            passed = milestone.get('passed')
            points_at_deadline = milestone.get('points_at_deadline', current_points)
            
            # Ensure points_at_deadline is a number
            if points_at_deadline is None:
                points_at_deadline = current_points
            
            if passed == True:
                status_class = "passed"
                status_text = "✅ PASSED"
            elif passed == False:
                status_class = "failed"
                status_text = "❌ FAILED"
            else:
                status_class = "pending"
                status_text = "⏳ IN PROGRESS"
            
            html_content += f"""
                    <div class="milestone {status_class}">
                        <strong>{title}</strong> - {status_text}<br>
                        Target: {target} | Achieved: {points_at_deadline:,} points
                    </div>
            """
        
        html_content += f"""
                    
                    <div class="alert">
                        <h3>⚠️ Required Actions</h3>
                        <ul>
                            <li>Review member performance data</li>
                            <li>Contact member for performance discussion</li>
                            <li>Consider probation extension or termination</li>
                            <li>Update member status in team management system</li>
                        </ul>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from the I.B.U Team Dashboard</p>
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create plain text version
        text_content = f"""
PROBATION FAILURE ALERT - {member_name}

URGENT: Member {member_name} has FAILED probation requirements.

Member Details:
- Name: {member_name}
- Joined: {joined_date}
- Days Since Joining: {days_since_joined}
- Current Points: {current_points:,}
- Failed Milestone(s): {failed_text}

Milestone Status:
"""
        
        for key, title, target in milestone_order:
            milestone = milestones.get(key, {})
            passed = milestone.get('passed')
            points_at_deadline = milestone.get('points_at_deadline', current_points)
            
            # Ensure points_at_deadline is a number
            if points_at_deadline is None:
                points_at_deadline = current_points
            
            status_text = "PASSED" if passed == True else "FAILED" if passed == False else "IN PROGRESS"
            text_content += f"- {title}: {status_text} (Target: {target}, Achieved: {points_at_deadline:,})\n"
        
        text_content += f"""
Required Actions:
- Review member performance data
- Contact member for performance discussion  
- Consider probation extension or termination
- Update member status in team management system

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return subject, html_content, text_content
    
    def send_email(self, to_emails: List[str], subject: str, html_content: str, text_content: str) -> bool:
        """Send email notification"""
        if not self.sender_email or not self.sender_password:
            print("Email credentials not configured. Skipping email notification.")
            return False
        
        if not to_emails:
            print("No recipient emails configured. Skipping email notification.")
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = ", ".join(to_emails)
            
            # Add both plain text and HTML parts
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Create secure connection and send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)
            
            print(f"Email notification sent successfully to: {', '.join(to_emails)}")
            return True
            
        except Exception as e:
            print(f"Error sending email notification: {e}")
            return False
    
    def notify_probation_failure(self, member_data: Dict) -> bool:
        """Send probation failure notification"""
        member_name = member_data.get('name', 'Unknown')
        
        # Check if we've already sent this notification
        if self.has_been_notified(member_name, "failed"):
            print(f"Already notified about {member_name} probation failure. Skipping duplicate.")
            return True
        
        # Create email content
        subject, html_content, text_content = self.create_failure_email(member_data)
        
        # Send email
        success = self.send_email(self.admin_emails, subject, html_content, text_content)
        
        if success:
            # Mark as notified to prevent duplicates
            self.mark_as_notified(member_name, "failed")
        
        return success
    
    def check_and_notify_failures(self, members_data: List[Dict], current_csv_file: str = None):
        """
        Check all members for failures and send notifications
        Only sends notifications if this is a new CSV file or a new day
        """
        # If no CSV file provided, skip the smart checking
        if current_csv_file and not self.should_check_for_notifications(current_csv_file):
            return
        
        failed_members = [m for m in members_data if m.get('probation_status') == 'failed']
        
        if not failed_members:
            print("✅ No failed members found in current data")
            if current_csv_file:
                self.update_csv_tracking(current_csv_file)
            return
        
        print(f"🚨 Found {len(failed_members)} failed members. Sending notifications...")
        
        notifications_sent = 0
        for member in failed_members:
            try:
                # For daily notifications, we need to check if this member was already notified today
                member_name = member.get('name', 'Unknown')
                today_key = f"{member_name}_failed_{self.last_notification_date}"
                
                if today_key not in self.notification_history:
                    success = self.notify_probation_failure(member)
                    if success:
                        notifications_sent += 1
                        # Mark as notified for today
                        self.notification_history[today_key] = {
                            "timestamp": datetime.now().isoformat(),
                            "member": member_name,
                            "status": "failed",
                            "csv_file": os.path.basename(current_csv_file) if current_csv_file else "unknown"
                        }
                else:
                    print(f"⏭️ Already notified about {member_name} today")
                    
            except Exception as e:
                print(f"❌ Error notifying about {member.get('name', 'Unknown')}: {e}")
        
        if notifications_sent > 0:
            print(f"✅ Sent {notifications_sent} probation failure notifications")
        
        # Update CSV tracking after processing
        if current_csv_file:
            self.update_csv_tracking(current_csv_file)

# Global notification service instance
notification_service = NotificationService()
