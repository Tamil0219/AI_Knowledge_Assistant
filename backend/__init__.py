"""
Backend Module for AI Cartoonization Platform
Contains database management, authentication, and business logic
"""

from backend.database import (
    DatabaseManager,
    initialize_database,
    UserDatabase,
    TransactionDatabase,
    ImageHistoryDatabase
)

from backend.auth import (
    validate_email,
    validate_password,
    hash_password,
    verify_password,
    register_user,
    login_user,
    AuthenticationError,
    EmailValidationError,
    PasswordValidationError
)

__all__ = [
    'DatabaseManager',
    'initialize_database',
    'UserDatabase',
    'TransactionDatabase',
    'ImageHistoryDatabase',
    'validate_email',
    'validate_password',
    'hash_password',
    'verify_password',
    'register_user',
    'login_user',
    'AuthenticationError',
    'EmailValidationError',
    'PasswordValidationError'
]
