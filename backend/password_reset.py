"""
Password reset helper: generate tokens, store them, and send reset emails.

This module handles password reset requests using the email_service module
for proper SMTP email sending with Gmail integration.

Environment Variables Required:
    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=587
    EMAIL_USER=your-email@gmail.com
    EMAIL_PASS=your-app-specific-password
    EMAIL_FROM=your-email@gmail.com

See backend/email_service.py for complete documentation and configuration.
"""
import secrets
import logging
from datetime import datetime, timedelta
import os
from backend.database import DatabaseManager, UserDatabase
from backend.email_service import (
    send_password_reset_email,
    is_email_configured,
    send_otp_email,
)
from pathlib import Path
import json

# Configure logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def send_reset_email(email: str, expires_hours: int = 1) -> tuple:
    """
    Generate a password reset token and send reset email to user.
    
    Args:
        email (str): User's email address
        expires_hours (int): Token expiration time in hours (default: 1)
    
    Returns:
        Tuple: (success: bool, token: str, message: str)
            - success: True if email sent successfully, False otherwise
            - token: The generated reset token
            - message: Status message for user feedback
    
    Example:
        >>> success, token, msg = send_reset_email("user@example.com")
        >>> if success:
        ...     print("Email sent successfully!")
    """
    logger.info(f"Password reset requested for: {email}")
    
    dbm = DatabaseManager()
    user_db = UserDatabase(dbm)
    
    # Generate token and expiry
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat()
    
    # Try to find user
    user = user_db.get_user_by_email(email)
    
    if user:
        # Store reset token in database
        try:
            user_db.create_password_reset(user['user_id'], token, expires_at)
            logger.info(f"Reset token created for user: {user['username']}")
        except Exception as e:
            logger.error(f"Failed to store reset token: {e}")
            return (False, token, f"Database error: {str(e)}")
    else:
        # Don't reveal if email exists (security best practice)
        logger.warning(f"Password reset requested for non-existent email: {email}")
    
    # Check if email service is configured
    if not is_email_configured():
        logger.warning("Email service not configured - would need SMTP setup")
        return (
            False,
            token,
            "Email service not configured. Please contact administrator to set up email."
        )
    
    # Prepare reset link
    reset_link = f"http://localhost:8501/?reset_token={token}"
    
    # Send email using email service
    try:
        logger.info(f"Sending password reset email to {email}...")
        success, message = send_password_reset_email(
            to_email=email,
            reset_link=reset_link,
            username=user['username'] if user else None
        )
        
        if success:
            logger.info(f"✅ Password reset email sent successfully to {email}")
            return (
                True,
                token,
                "If this email is registered, a password reset link has been sent."
            )
        else:
            logger.error(f"Failed to send password reset email: {message}")
            return (False, token, f"Email sending failed: {message}")
            
    except Exception as e:
        logger.error(f"Exception while sending password reset email: {e}")
        return (False, token, f"Error sending email: {str(e)}")


def _generate_numeric_otp(length: int = 6) -> str:
    """Generate a zero-padded numeric OTP of given length."""
    max_val = 10 ** length
    otp_int = secrets.randbelow(max_val)
    return str(otp_int).zfill(length)


def send_otp(email: str, expires_minutes: int = 10) -> tuple:
    """
    Generate a numeric OTP, store it in PasswordResets, and send it via email.

    Returns: (success: bool, otp: str (hidden on failures), message: str)
    """
    logger.info(f"OTP password reset requested for: {email}")

    dbm = DatabaseManager()
    user_db = UserDatabase(dbm)

    # Generate OTP and expiry
    otp = _generate_numeric_otp(6)
    expires_at = (datetime.utcnow() + timedelta(minutes=expires_minutes)).isoformat()

    # Try to find user
    user = user_db.get_user_by_email(email)

    if user:
        # Store OTP in database (token field)
        # Ensure unique token by retrying a few times on IntegrityError
        attempts = 0
        stored = None
        while attempts < 5 and not stored:
            try:
                stored = user_db.create_password_reset(user['user_id'], otp, expires_at)
            except Exception as e:
                logger.warning(f"OTP token collision, regenerating... ({e})")
                otp = _generate_numeric_otp(6)
                attempts += 1

        if not stored:
            logger.error("Failed to store OTP in database after retries")
            return (False, otp, "Failed to create OTP record. Try again later.")
    else:
        # Do not reveal whether email exists; still proceed to pretend to send
        logger.warning(f"OTP requested for non-existent email: {email}")

    # Check email configuration
    if not is_email_configured():
        logger.warning("Email service not configured - cannot send OTP")
        return (
            False,
            otp,
            "Email service not configured. Please contact administrator."
        )

    # Send OTP email
    try:
        username = user['username'] if user else None
        success, message = send_otp_email(to_email=email, otp=otp, minutes_valid=expires_minutes, username=username)
        if success:
            logger.info(f"OTP sent to {email}")
            return (True, otp, "If this email is registered, an OTP has been sent.")
        else:
            logger.error(f"Failed to send OTP email: {message}")
            # Fallback: write OTP to outputs/emails for local testing
            try:
                project_root = Path(__file__).resolve().parents[1]
                out_dir = project_root / 'outputs' / 'emails'
                out_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                safe_email = email.replace('@', '_at_').replace('.', '_')
                fname = f"reset_{safe_email}_{otp}_{timestamp}.txt"
                fpath = out_dir / fname
                body = {
                    'to': email,
                    'subject': 'AI Cartoonization - Password Reset OTP (fallback)',
                    'otp': otp,
                    'valid_minutes': expires_minutes,
                    'username': username,
                    'note': 'This file was written because email sending failed. Use the OTP to reset the password in the app.'
                }
                fpath.write_text(json.dumps(body, indent=2))
                logger.info(f"Wrote fallback OTP file to {fpath}")
                return (True, otp, f"Email sending failed; OTP written to outputs/emails for testing ({fname}).")
            except Exception as e:
                logger.error(f"Failed to write fallback OTP file: {e}")
                return (False, otp, f"Email sending failed and fallback failed: {message}; {e}")

    except Exception as e:
        logger.error(f"Exception while sending OTP email: {e}")
        # Fallback to writing OTP file
        try:
            project_root = Path(__file__).resolve().parents[1]
            out_dir = project_root / 'outputs' / 'emails'
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            safe_email = email.replace('@', '_at_').replace('.', '_')
            fname = f"reset_{safe_email}_{otp}_{timestamp}.txt"
            fpath = out_dir / fname
            body = {
                'to': email,
                'subject': 'AI Cartoonization - Password Reset OTP (fallback)',
                'otp': otp,
                'valid_minutes': expires_minutes,
                'username': user['username'] if user else None,
                'note': 'This file was written because email sending raised an exception. Use the OTP to reset the password in the app.'
            }
            fpath.write_text(json.dumps(body, indent=2))
            logger.info(f"Wrote fallback OTP file to {fpath}")
            return (True, otp, f"Error sending email; OTP written to outputs/emails for testing ({fname}).")
        except Exception as e2:
            logger.error(f"Failed to write fallback OTP file after exception: {e2}")
            return (False, otp, f"Error sending email and fallback failed: {str(e)}; {str(e2)}")


def verify_otp_and_reset_password(email: str, otp: str, new_password_hash: str) -> tuple:
    """
    Verify an OTP for the given email and, if valid, set the new password hash.

    Returns: (success: bool, message: str)
    """
    logger.info(f"Verifying OTP for {email}")

    dbm = DatabaseManager()
    user_db = UserDatabase(dbm)

    user = user_db.get_user_by_email(email)
    if not user:
        logger.warning("OTP verification attempted for non-existent email")
        return (False, "Invalid OTP or email")

    pr = user_db.get_password_reset(otp)
    if not pr:
        return (False, "Invalid or expired OTP")

    # Ensure OTP belongs to this user
    if pr.get('user_id') != user['user_id']:
        return (False, "Invalid OTP for this email")

    # Check used
    if pr.get('used'):
        return (False, "This OTP has already been used")

    # Check expiry
    try:
        expires_at = datetime.fromisoformat(pr.get('expires_at'))
    except Exception:
        return (False, "Invalid OTP expiry format")

    if expires_at < datetime.utcnow():
        return (False, "This OTP has expired")

    # Update password
    try:
        updated = user_db.update_password_hash(user['user_id'], new_password_hash)
        if not updated:
            return (False, "Failed to update password. Please try again later.")

        # Mark OTP used and reset failed attempts
        user_db.mark_password_reset_used(otp)
        user_db.reset_failed_attempts(user['user_id'])

        return (True, "Password has been reset successfully.")

    except Exception as e:
        logger.error(f"Error while resetting password for user {user['user_id']}: {e}")
        return (False, f"Error resetting password: {str(e)}")
