#!/usr/bin/env python3
"""
Email Service Verification and Testing Script

Run this script to verify your email service configuration and test email sending.

Usage:
    python test_email_config.py          # Check configuration
    python test_email_config.py --test   # Send test email
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.email_service import (
    is_email_configured,
    send_email,
    send_password_reset_email,
    EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_FROM, EMAIL_TIMEOUT
)


def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def check_configuration():
    """Check if email service is properly configured"""
    print_header("EMAIL SERVICE CONFIGURATION CHECK")
    
    config = {
        'EMAIL_HOST': EMAIL_HOST,
        'EMAIL_PORT': EMAIL_PORT,
        'EMAIL_USER': EMAIL_USER,
        'EMAIL_FROM': EMAIL_FROM,
        'EMAIL_TIMEOUT': EMAIL_TIMEOUT,
    }
    
    print("\nConfiguration Status:")
    print("-" * 70)
    
    for key, value in config.items():
        if key == 'EMAIL_USER':
            status = "✅ SET" if value else "❌ NOT SET"
        else:
            status = f"✅ {value}" if value else "❌ NOT SET"
        print(f"  {key:<20} : {status}")
    
    print("-" * 70)
    
    if is_email_configured():
        print("\n✅ Email service is CONFIGURED and ready to use!\n")
        return True
    else:
        print("\n❌ Email service is NOT properly configured.\n")
        print("Next steps:")
        print("  1. Copy .env.example to .env")
        print("  2. Edit .env with your Gmail credentials")
        print("  3. For Gmail, generate an App Password at:")
        print("     https://myaccount.google.com/apppasswords")
        print("  4. Run this script again to verify\n")
        return False


def test_email_sending():
    """Test sending a test email"""
    print_header("EMAIL SENDING TEST")
    
    if not is_email_configured():
        print("\n❌ Email service is not configured!")
        print("Please configure email first (see EMAIL_SETUP_GUIDE.md)\n")
        return False
    
    # Get test email from user
    test_email = input("\nEnter test email address: ").strip()
    
    if not test_email or '@' not in test_email:
        print("\n❌ Invalid email address\n")
        return False
    
    # Send test email
    print(f"\nSending test email to {test_email}...")
    
    success, message = send_email(
        to_email=test_email,
        subject="AI Cartoonization - Email Service Test",
        html_body="""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white; padding: 20px; border-radius: 10px;">
                    <h2>Email Service Test</h2>
                    <p>This is a test email from AI Cartoonization Platform.</p>
                    <p>If you received this email, the email service is working correctly! ✅</p>
                </div>
            </body>
        </html>
        """,
        text_body="Test email from AI Cartoonization Platform. The email service is working!"
    )
    
    if success:
        print(f"\n✅ SUCCESS: {message}")
        print(f"Check {test_email} for the test email.\n")
        return True
    else:
        print(f"\n❌ FAILED: {message}\n")
        return False


def test_password_reset_email():
    """Test sending a password reset email"""
    print_header("PASSWORD RESET EMAIL TEST")
    
    if not is_email_configured():
        print("\n❌ Email service is not configured!")
        print("Please configure email first\n")
        return False
    
    # Get test details from user
    test_email = input("Enter test email address: ").strip()
    username = input("Enter username (optional): ").strip() or None
    
    if not test_email or '@' not in test_email:
        print("\n❌ Invalid email address\n")
        return False
    
    # Create test reset link
    test_link = "http://localhost:8501/?reset_token=test_token_abcdef123456"
    
    print(f"\nSending password reset email to {test_email}...")
    
    success, message = send_password_reset_email(
        to_email=test_email,
        reset_link=test_link,
        username=username
    )
    
    if success:
        print(f"\n✅ SUCCESS: {message}")
        print(f"Check {test_email} for the password reset email.\n")
        return True
    else:
        print(f"\n❌ FAILED: {message}\n")
        return False


def show_debug_info():
    """Show debug information"""
    print_header("DEBUG INFORMATION")
    
    print("\n.env file location:")
    print(f"  {os.path.abspath('.env')}")
    
    print("\nEnvironment variables loaded:")
    print(f"  EMAIL_HOST: {os.environ.get('EMAIL_HOST', 'NOT SET')}")
    print(f"  EMAIL_PORT: {os.environ.get('EMAIL_PORT', 'NOT SET')}")
    print(f"  EMAIL_USER: {os.environ.get('EMAIL_USER', 'NOT SET')}")
    print(f"  EMAIL_PASS: {'*' * 10 if os.environ.get('EMAIL_PASS') else 'NOT SET'}")
    print(f"  EMAIL_FROM: {os.environ.get('EMAIL_FROM', 'NOT SET')}")
    print()


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Run full test
        check_configuration()
        
        if is_email_configured():
            print("\nSelect test to run:")
            print("  1. Send test email")
            print("  2. Send password reset email")
            print("  3. Show debug info")
            print("  4. Exit")
            
            choice = input("\nEnter choice (1-4): ").strip()
            
            if choice == '1':
                test_email_sending()
            elif choice == '2':
                test_password_reset_email()
            elif choice == '3':
                show_debug_info()
            else:
                print("\nExiting...\n")
    else:
        # Just check configuration
        check_configuration()
        show_debug_info()
        
        print("\nTo run full tests, use:")
        print("  python test_email_config.py --test\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
