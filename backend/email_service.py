"""
Production-ready Email Service for AI Cartoonization Platform.

This module handles sending emails via SMTP with proper security, 
error handling, and logging. Supports both plain text and HTML emails.

Environment Variables Required:
- EMAIL_HOST: SMTP server address (e.g., 'smtp.gmail.com')
- EMAIL_PORT: SMTP port (default: 587 for TLS)
- EMAIL_USER: Email account username
- EMAIL_PASS: Email account password or app-specific password
- EMAIL_FROM: Sender email address (defaults to EMAIL_USER)
- EMAIL_TIMEOUT: Connection timeout in seconds (default: 10)

Example .env file:
    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=587
    EMAIL_USER=your-email@gmail.com
    EMAIL_PASS=your-app-specific-password
    EMAIL_FROM=your-email@gmail.com
    EMAIL_TIMEOUT=10

For Gmail Setup:
1. Enable 2-Step Verification in your Google Account
2. Generate an App Password at: https://myaccount.google.com/apppasswords
3. Use the 16-character password as EMAIL_PASS
4. Never use your regular Gmail password in environment variables
"""

import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Email configuration from environment variables
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')
EMAIL_FROM = os.environ.get('EMAIL_FROM', EMAIL_USER)
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '10'))


def is_email_configured() -> bool:
    """
    Check if email service is properly configured.
    
    Returns:
        bool: True if all required environment variables are set
    """
    required = [EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASS]
    return all(required)


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str = None,
    retry_count: int = 3
) -> Tuple[bool, str]:
    """
    Send an email using SMTP with TLS security.
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject line
        html_body (str): HTML email body
        text_body (str, optional): Plain text fallback. Auto-generated if not provided.
        retry_count (int): Number of retry attempts (default: 3)
    
    Returns:
        Tuple[bool, str]: (success: bool, message: str)
            - (True, "Email sent successfully") on success
            - (False, error_message) on failure
    
    Example:
        >>> success, message = send_email(
        ...     to_email="user@example.com",
        ...     subject="Password Reset",
        ...     html_body="<p>Click <a href='...'>here</a> to reset</p>",
        ...     text_body="Click the link to reset your password"
        ... )
    """
    
    # Check configuration
    if not is_email_configured():
        logger.error(
            'Email service not configured. Missing: '
            f'EMAIL_HOST={EMAIL_HOST}, EMAIL_USER={EMAIL_USER}'
        )
        return (
            False,
            'Email service is not configured. Please set environment variables: '
            'EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASS'
        )
    
    # Validate email address
    if not to_email or '@' not in to_email:
        logger.warning(f'Invalid recipient email: {to_email}')
        return False, 'Invalid recipient email address'
    
    # Use HTML body as text if not provided
    if not text_body:
        # Simple HTML to text conversion
        text_body = html_body.replace('<p>', '').replace('</p>', '\n')
        text_body = text_body.replace('<br>', '\n').replace('<br/>', '\n')
        text_body = text_body.replace('<a href=\'', '').replace('\'>', ' - ')
        text_body = text_body.replace('<a href="', '').replace('">', ' - ')
        text_body = text_body.replace('</a>', '')
    
    # Create email message
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        msg['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
        
        # Attach plain text and HTML versions
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
    except Exception as e:
        logger.error(f'Failed to create email message: {e}')
        return False, f'Failed to create email message: {str(e)}'
    
    # Send email with retry logic
    for attempt in range(1, retry_count + 1):
        try:
            logger.info(
                f'Attempt {attempt}/{retry_count}: '
                f'Connecting to {EMAIL_HOST}:{EMAIL_PORT}...'
            )
            
            # Create SMTP connection
            server = smtplib.SMTP(
                EMAIL_HOST,
                EMAIL_PORT,
                timeout=EMAIL_TIMEOUT
            )
            server.set_debuglevel(0)  # Set to 1 for debug output
            
            # Start TLS encryption
            logger.info('Starting TLS encryption...')
            server.starttls()
            
            # Authenticate
            logger.info(f'Authenticating as {EMAIL_USER}...')
            server.login(EMAIL_USER, EMAIL_PASS)
            
            # Send email
            logger.info(f'Sending email to {to_email}...')
            server.send_message(msg)
            
            # Close connection
            server.quit()
            
            logger.info(f'✅ Email sent successfully to {to_email}')
            return True, 'Email sent successfully'
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = (
                'SMTP Authentication failed. Check EMAIL_USER and EMAIL_PASS. '
                'For Gmail, use an App Password, not your regular password.'
            )
            logger.error(f'{error_msg}: {e}')
            if attempt == retry_count:
                return False, error_msg
                
        except smtplib.SMTPException as e:
            error_msg = f'SMTP error occurred (attempt {attempt}/{retry_count}): {str(e)}'
            logger.error(error_msg)
            if attempt == retry_count:
                return False, error_msg
                
        except OSError as e:
            error_msg = (
                f'Network error (attempt {attempt}/{retry_count}): {str(e)}. '
                f'Check EMAIL_HOST ({EMAIL_HOST}) and EMAIL_PORT ({EMAIL_PORT})'
            )
            logger.error(error_msg)
            if attempt == retry_count:
                return False, error_msg
                
        except Exception as e:
            error_msg = f'Unexpected error (attempt {attempt}/{retry_count}): {str(e)}'
            logger.error(error_msg)
            if attempt == retry_count:
                return False, error_msg
    
    return False, 'Failed to send email after all retry attempts'


def send_password_reset_email(
    to_email: str,
    reset_link: str,
    username: str = None
) -> Tuple[bool, str]:
    """
    Send a password reset email with a pre-formatted template.
    
    Args:
        to_email (str): Recipient email address
        reset_link (str): Full password reset URL
        username (str, optional): User's name for personalization
    
    Returns:
        Tuple[bool, str]: (success: bool, message: str)
    
    Example:
        >>> success, msg = send_password_reset_email(
        ...     to_email="user@example.com",
        ...     reset_link="http://localhost:8501/?reset_token=abc123",
        ...     username="John Doe"
        ... )
    """
    
    subject = 'AI Cartoonization Platform - Password Reset Request'
    
    # HTML email template
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            color: white; padding: 30px; border-radius: 10px; text-align: center;">
                    <h1 style="margin: 0; font-size: 2em;">🎨 AI Cartoonization</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Password Reset Request</p>
                </div>
                
                <div style="padding: 30px 0;">
                    <p>Hello{' ' + username if username else ''},</p>
                    
                    <p>We received a request to reset your password. 
                    If you didn't make this request, you can safely ignore this email.</p>
                    
                    <p>To reset your password, click the button below 
                    (valid for 1 hour):</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" 
                           style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                  color: white;
                                  padding: 12px 30px;
                                  text-decoration: none;
                                  border-radius: 5px;
                                  font-weight: bold;
                                  display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    
                    <p style="font-size: 0.9em; color: #666;">
                        Or copy and paste this link in your browser:<br>
                        <code style="background: #f0f0f0; padding: 5px; border-radius: 3px; 
                                    word-break: break-all;">{reset_link}</code>
                    </p>
                </div>
                
                <div style="border-top: 1px solid #ddd; padding-top: 20px; 
                           font-size: 0.85em; color: #999; text-align: center;">
                    <p>© 2026 AI Cartoonization Platform. All rights reserved.</p>
                    <p>If you have questions, please contact our support team.</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    # Plain text version
    text_body = f"""
AI Cartoonization - Password Reset Request

Hello{' ' + username if username else ''},

We received a request to reset your password. If you didn't make this request, 
you can safely ignore this email.

To reset your password, visit this link (valid for 1 hour):
{reset_link}

If you have questions, please contact our support team.

© 2026 AI Cartoonization Platform. All rights reserved.
"""
    
    return send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )


def send_otp_email(
    to_email: str,
    otp: str,
    minutes_valid: int = 10,
    username: str = None
) -> Tuple[bool, str]:
    """
    Send a one-time password (OTP) email to the user.

    Args:
        to_email: Recipient email address
        otp: Numeric OTP string to include in the email
        minutes_valid: Minutes the OTP is valid for (display only)
        username: Optional user name for personalization

    Returns:
        Tuple[bool, str]: (success, message)
    """

    subject = 'AI Cartoonization - Your One-Time Password (OTP)'

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            color: white; padding: 30px; border-radius: 10px; text-align: center;">
                    <h1 style="margin: 0; font-size: 2em;">🔐 AI Cartoonization</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Password Reset OTP</p>
                </div>

                <div style="padding: 30px 0; text-align: center;">
                    <p>Hello{' ' + username if username else ''},</p>
                    <p>Use the following one-time password to reset your account password. This code is valid for {minutes_valid} minutes.</p>
                    <div style="font-size: 2em; font-weight: bold; margin: 20px 0;">{otp}</div>
                    <p style="color: #666; font-size: 0.9em;">If you did not request a password reset, please ignore this email.</p>
                </div>

                <div style="border-top: 1px solid #ddd; padding-top: 20px; 
                           font-size: 0.85em; color: #999; text-align: center;">
                    <p>© 2026 AI Cartoonization Platform. All rights reserved.</p>
                </div>
            </div>
        </body>
    </html>
    """

    text_body = f"""
AI Cartoonization - Password Reset OTP

Hello{' ' + username if username else ''},

Use the following one-time password to reset your account password. This code is valid for {minutes_valid} minutes.

{otp}

If you did not request a password reset, please ignore this email.

© 2026 AI Cartoonization Platform. All rights reserved.
    """

    return send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )


# Example usage and testing
if __name__ == '__main__':
    # Test configuration
    print("\n" + "="*70)
    print("EMAIL SERVICE CONFIGURATION TEST")
    print("="*70)
    
    config_status = {
        'EMAIL_HOST': EMAIL_HOST or "❌ NOT SET",
        'EMAIL_PORT': EMAIL_PORT or "❌ NOT SET",
        'EMAIL_USER': '✓ SET' if EMAIL_USER else "❌ NOT SET",
        'EMAIL_PASS': '✓ SET (hidden)' if EMAIL_PASS else "❌ NOT SET",
        'EMAIL_FROM': EMAIL_FROM or "❌ NOT SET",
    }
    
    print("\nConfiguration Status:")
    for key, value in config_status.items():
        print(f"  {key}: {value}")
    
    print(f"\nEmail Service Configured: {is_email_configured()}")
    
    if is_email_configured():
        print("\n✅ Ready to send emails!")
    else:
        print("\n❌ Email service not configured.")
        print("\nTo set up email, create a .env file with:")
        print("""
    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=587
    EMAIL_USER=your-email@gmail.com
    EMAIL_PASS=your-app-specific-password
    EMAIL_FROM=your-email@gmail.com
        """)
    
    print("\n" + "="*70 + "\n")
