"""
Authentication Module for AI Cartoonization Platform
Handles user registration, login, and password management
"""

import re
import bcrypt
from typing import Tuple, Dict, Optional
from backend.database import UserDatabase, DatabaseManager


class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    pass


class EmailValidationError(AuthenticationError):
    """Raised when email validation fails"""
    pass


class PasswordValidationError(AuthenticationError):
    """Raised when password validation fails"""
    pass


class UserRegistrationError(AuthenticationError):
    """Raised when user registration fails"""
    pass


def validate_email(email: str) -> bool:
    """
    Validate email format using regex
    
    Args:
        email: Email address to validate
    
    Returns:
        bool: True if email is valid, False otherwise
    
    Raises:
        EmailValidationError: If email is invalid
    """
    if not email:
        raise EmailValidationError("Email cannot be empty")
    
    # RFC 5322 compliant email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email.strip()):
        raise EmailValidationError(
            "Invalid email format. Please enter a valid email address."
        )
    
    # Additional validation: check length
    if len(email) > 254:
        raise EmailValidationError("Email address is too long")
    
    return True


def validate_password(password: str) -> bool:
    """
    Validate password strength
    
    Requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    - At least 1 special character
    
    Args:
        password: Password to validate
    
    Returns:
        bool: True if password meets all requirements
    
    Raises:
        PasswordValidationError: If password doesn't meet requirements
    """
    if not password:
        raise PasswordValidationError("Password cannot be empty")
    
    errors = []
    
    # Check minimum length
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least 1 uppercase letter")
    
    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least 1 lowercase letter")
    
    # Check for number
    if not re.search(r'[0-9]', password):
        errors.append("Password must contain at least 1 number")
    
    # Check for special character
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        errors.append("Password must contain at least 1 special character (!@#$%^&*...)")
    
    if errors:
        raise PasswordValidationError(
            "Password requirements not met:\n" + "\n".join(f"• {error}" for error in errors)
        )
    
    return True


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password to hash
    
    Returns:
        str: Hashed password
    
    Raises:
        Exception: If hashing fails
    """
    try:
        # Hash the password with bcrypt
        # Using default cost factor of 12
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        raise AuthenticationError(f"Failed to hash password: {str(e)}")


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        password: Plain text password to verify
        hashed_password: Previously hashed password
    
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        print(f"Error verifying password: {str(e)}")
        return False


def register_user(username: str, email: str, password: str,
                 db_manager: Optional[DatabaseManager] = None) -> Tuple[bool, str, Optional[int]]:
    """
    Register a new user with validation and database insertion
    
    Args:
        username: User's username (must be unique)
        email: User's email (must be unique and valid)
        password: User's password (must meet strength requirements)
        db_manager: Optional DatabaseManager instance
    
    Returns:
        Tuple[bool, str, Optional[int]]: (success, message, user_id)
        - success: True if registration successful, False otherwise
        - message: Success or error message
        - user_id: User ID if successful, None otherwise
    
    Example:
        >>> success, message, user_id = register_user("john_doe", "john@example.com", "SecurePass123!")
        >>> if success:
        >>>     print(f"User registered with ID: {user_id}")
        >>> else:
        >>>     print(f"Registration failed: {message}")
    """
    try:
        # Initialize database manager if not provided
        if db_manager is None:
            db_manager = DatabaseManager()
        
        user_db = UserDatabase(db_manager)
        
        # Input validation
        username = username.strip() if username else ""
        email = email.strip() if email else ""
        
        # Validate username
        if not username:
            return False, "Username cannot be empty", None
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters long", None
        
        if len(username) > 50:
            return False, "Username must not exceed 50 characters", None
        
        # Check if username contains only valid characters
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, hyphens, and underscores", None
        
        # Validate email format
        try:
            validate_email(email)
        except EmailValidationError as e:
            return False, str(e), None
        
        # Validate password strength
        try:
            validate_password(password)
        except PasswordValidationError as e:
            return False, str(e), None
        
        # Check if username already exists
        existing_user = user_db.get_user_by_username(username)
        if existing_user:
            return False, f"Username '{username}' is already taken. Please choose a different username.", None
        
        # Check if email already exists
        existing_email = user_db.get_user_by_email(email)
        if existing_email:
            return False, f"Email '{email}' is already registered. Please use a different email or login.", None
        
        # Hash the password
        try:
            password_hash = hash_password(password)
        except AuthenticationError as e:
            return False, str(e), None
        
        # Create user in database
        try:
            user_id = user_db.create_user(username, email, password_hash)
            
            if user_id:
                return (
                    True,
                    f"User '{username}' registered successfully! You can now login.",
                    user_id
                )
            else:
                return (
                    False,
                    "Failed to create user account. Please try again later.",
                    None
                )
        except Exception as e:
            return False, f"Database error during registration: {str(e)}", None
    
    except Exception as e:
        print(f"Unexpected error during registration: {str(e)}")
        return False, "An unexpected error occurred during registration. Please try again.", None


def login_user(identifier: str, password: str,
              db_manager: Optional[DatabaseManager] = None) -> Tuple[bool, str, Optional[Dict]]:
    """
    Authenticate a user with email or username and password
    
    Args:
        identifier: User's email address or username
        password: User's password
        db_manager: Optional DatabaseManager instance
    
    Returns:
        Tuple[bool, str, Optional[Dict]]: (success, message, user_data)
        - success: True if login successful, False otherwise
        - message: Success or error message with specific reason
        - user_data: User information if successful, None otherwise
    
    Handles:
        - Login with email or username
        - Account locking after 5 failed attempts
        - Password verification using bcrypt
        - Failed attempt tracking
        - Last login timestamp update
    
    Example:
        >>> # Login with email
        >>> success, message, user = login_user("john@example.com", "SecurePass123!")
        >>> # Login with username
        >>> success, message, user = login_user("john_doe", "SecurePass123!")
        >>> if success:
        >>>     print(f"Welcome back, {user['username']}!")
        >>> else:
        >>>     print(f"Login failed: {message}")
    """
    try:
        if db_manager is None:
            db_manager = DatabaseManager()
        
        user_db = UserDatabase(db_manager)
        
        # Validate inputs
        identifier = identifier.strip() if identifier else ""
        
        if not identifier or not password:
            return False, "Email/Username and password are required", None
        
        # Try to get user by email first, then by username
        user = None
        identifier_type = None
        
        if '@' in identifier:
            # Likely an email
            try:
                validate_email(identifier)
                user = user_db.get_user_by_email(identifier)
                identifier_type = "email"
            except EmailValidationError:
                # Not a valid email format, try as username
                user = user_db.get_user_by_username(identifier)
                identifier_type = "username"
        else:
            # Try as username first
            user = user_db.get_user_by_username(identifier)
            identifier_type = "username"
            
            # If not found, might be a malformed email, try email lookup
            if not user:
                user = user_db.get_user_by_email(identifier)
                identifier_type = "email"
        
        # User not found
        if not user:
            return False, "User not found. Please check your email/username or register a new account.", None
        
        # Check if account is locked due to too many failed attempts
        if user['failed_attempts'] >= 5:
            return (
                False,
                "🔒 Account locked due to too many failed login attempts. "
                "Please contact support or use password reset.",
                None
            )
        
        # Verify password
        if not verify_password(password, user['password_hash']):
            # Increment failed attempts
            user_db.increment_failed_attempts(user['user_id'])
            
            # Check if account is now locked
            attempts_remaining = 5 - (user['failed_attempts'] + 1)
            if attempts_remaining > 0:
                return (
                    False,
                    f"Invalid password. {attempts_remaining} attempt{'s' if attempts_remaining != 1 else ''} remaining before account lock.",
                    None
                )
            else:
                return (
                    False,
                    "🔒 Account locked due to too many failed login attempts. "
                    "Please contact support or use password reset.",
                    None
                )
        
        # Password is correct - reset failed attempts and update last login
        try:
            user_db.reset_failed_attempts(user['user_id'])
            user_db.update_last_login(user['user_id'])
        except Exception as db_error:
            print(f"Warning: Failed to update user status: {str(db_error)}")
            # Continue anyway as the login was successful
        
        # Remove password hash from returned user data for security
        user_safe = {k: v for k, v in user.items() if k != 'password_hash'}
        
        return True, f"Welcome back, {user['username']}!", user_safe
    
    except Exception as e:
        print(f"Error during login: {str(e)}")
        return False, "An error occurred during login. Please try again later.", None


# Example usage for testing
if __name__ == "__main__":
    # Test email validation
    print("=" * 50)
    print("Testing Email Validation")
    print("=" * 50)
    test_emails = [
        "valid@example.com",
        "user.name+tag@example.co.uk",
        "invalid.email@",
        "missing@domain",
        ""
    ]
    
    for test_email in test_emails:
        try:
            validate_email(test_email)
            print(f"✅ {test_email} - Valid")
        except EmailValidationError as e:
            print(f"❌ {test_email} - {e}")
    
    # Test password validation
    print("\n" + "=" * 50)
    print("Testing Password Validation")
    print("=" * 50)
    test_passwords = [
        "Weak",
        "NoNumbers!",
        "NoSpecial123",
        "noupppercase123!",
        "ValidPass123!"
    ]
    
    for test_pass in test_passwords:
        try:
            validate_password(test_pass)
            print(f"✅ {test_pass} - Valid")
        except PasswordValidationError as e:
            print(f"❌ {test_pass}")
            print(f"   {e}\n")
    
    # Test password hashing
    print("=" * 50)
    print("Testing Password Hashing")
    print("=" * 50)
    test_password = "ValidPass123!"
    hashed = hash_password(test_password)
    print(f"Original: {test_password}")
    print(f"Hashed: {hashed}")
    print(f"Verification: {verify_password(test_password, hashed)}")
    
    # Test user registration
    print("\n" + "=" * 50)
    print("Testing User Registration")
    print("=" * 50)
    success, message, user_id = register_user(
        "test_user",
        "testuser@example.com",
        "TestPass123!"
    )
    print(f"Success: {success}")
    print(f"Message: {message}")
    if user_id:
        print(f"User ID: {user_id}")
    
    # Test login with email
    print("\n" + "=" * 50)
    print("Testing Login with Email")
    print("=" * 50)
    success, message, user = login_user("testuser@example.com", "TestPass123!")
    print(f"Success: {success}")
    print(f"Message: {message}")
    if user:
        print(f"User ID: {user['user_id']}, Username: {user['username']}")
    
    # Test login with username
    print("\n" + "=" * 50)
    print("Testing Login with Username")
    print("=" * 50)
    success, message, user = login_user("test_user", "TestPass123!")
    print(f"Success: {success}")
    print(f"Message: {message}")
    if user:
        print(f"User ID: {user['user_id']}, Username: {user['username']}")
    
    # Test login with wrong password
    print("\n" + "=" * 50)
    print("Testing Login with Wrong Password")
    print("=" * 50)
    success, message, user = login_user("testuser@example.com", "WrongPass123!")
    print(f"Success: {success}")
    print(f"Message: {message}")
    print(f"User: {user}")
    
    # Test login with non-existent user
    print("\n" + "=" * 50)
    print("Testing Login with Non-existent User")
    print("=" * 50)
    success, message, user = login_user("nonexistent@example.com", "TestPass123!")
    print(f"Success: {success}")
    print(f"Message: {message}")
    print(f"User: {user}")
