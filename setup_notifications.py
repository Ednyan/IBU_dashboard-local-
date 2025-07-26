#!/usr/bin/env python3
"""
Quick setup script for I.B.U Dashboard email notifications
"""

import os
import sys

def create_env_file():
    """Create .env file from example if it doesn't exist"""
    env_file = ".env"
    example_file = ".env.example"
    
    if os.path.exists(env_file):
        print("✅ .env file already exists")
        return True
    
    if not os.path.exists(example_file):
        print("❌ .env.example file not found")
        return False
    
    try:
        # Copy example to .env
        with open(example_file, 'r') as src:
            with open(env_file, 'w') as dst:
                dst.write(src.read())
        
        print("✅ Created .env file from .env.example")
        print("📝 Please edit .env file with your email configuration")
        return True
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import dotenv
        print("✅ python-dotenv is installed")
        return True
    except ImportError:
        print("❌ python-dotenv not installed")
        print("   Run: pip install python-dotenv")
        return False

def main():
    print("🚀 I.B.U Dashboard Email Notification Setup")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("\n📦 Install missing dependencies first:")
        print("   pip install -r requirements.txt")
        return False
    
    # Create .env file
    if not create_env_file():
        return False
    
    print("\n📋 Next Steps:")
    print("1. Edit .env file with your email settings:")
    print("   - SENDER_EMAIL: Your email address")
    print("   - SENDER_PASSWORD: Your email app password")
    print("   - ADMIN_EMAILS: Comma-separated list of notification recipients")
    print("2. Restart your Flask application")
    print("3. Visit /notification_admin to test the setup")
    
    print("\n💡 Gmail Users:")
    print("   - Use an App Password, not your regular password")
    print("   - Enable 2-Step Verification first")
    print("   - Generate App Password: Google Account > Security > App passwords")
    
    print("\n🔗 Access notification admin panel:")
    print("   http://localhost:5000/notification_admin")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
