"""
SQLite Database Module for AI Cartoonization Platform
Handles all database operations and schema management
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, List, Tuple


# Database configuration
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'app.db')
DB_DIR = os.path.dirname(DB_PATH)


def get_db_connection():
    """Get database connection for all database operations."""
    from pathlib import Path
    db_path = Path("database") / "app.db"
    return sqlite3.connect(str(db_path))


class DatabaseManager:
    """Manages SQLite database operations for AI Cartoonization Platform"""
    
    def __init__(self, db_path: str = DB_PATH):
        """Initialize database manager with specified path"""
        self.db_path = db_path
        self._ensure_db_directory()
    
    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        os.makedirs(DB_DIR, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with foreign keys enabled"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Tuple]:
        """Execute a SELECT query and return results"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute multiple INSERT/UPDATE/DELETE queries"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()


def initialize_database(db_path: str = DB_PATH) -> bool:
    """
    Initialize the database by creating all required tables if they don't exist.
    
    Args:
        db_path: Path to the SQLite database file
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign key support
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                failed_attempts INTEGER DEFAULT 0,
                two_factor_enabled INTEGER DEFAULT 0
            )
        """)
        
        # Create Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_id TEXT,
                payment_id TEXT,
                amount REAL,
                status TEXT,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            )
        """)
        
        # Create ImageHistory table (plus optional analytics fields)
        # New columns such as processing_time_seconds and intensity_level were
        # added later; ensure they exist for both fresh installs and upgrades.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ImageHistory (
                image_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_image_path TEXT NOT NULL,
                processed_image_path TEXT,
                style_applied TEXT,
                processing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payment_status TEXT,
                processing_time_seconds REAL,
                intensity_level TEXT,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            )
        """
        )
        # After creating the table we may still need to migrate existing databases
        # that were created before the new columns were introduced. Run PRAGMA
        # table_info and add any missing columns.
        cursor.execute("PRAGMA table_info(ImageHistory)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        # helper to add column if missing
        if 'processing_time_seconds' not in existing_cols:
            cursor.execute(
                "ALTER TABLE ImageHistory ADD COLUMN processing_time_seconds REAL"
            )
        if 'intensity_level' not in existing_cols:
            cursor.execute(
                "ALTER TABLE ImageHistory ADD COLUMN intensity_level TEXT"
            )
        
        # Create indexes for better query performance
        # Index on Users email for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email 
            ON Users(email)
        """)
        
        # Index on Users username for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username 
            ON Users(username)
        """)
        
        # Index on Transactions user_id for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_user_id 
            ON Transactions(user_id)
        """)
        
        # Index on Transactions transaction_date for time-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_date 
            ON Transactions(transaction_date)
        """)
        
        # Index on ImageHistory user_id for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_imagehistory_user_id 
            ON ImageHistory(user_id)
        """)
        
        # Index on ImageHistory processing_date for time-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_imagehistory_date 
            ON ImageHistory(processing_date)
        """)

        # Create PasswordResets table for password reset tokens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS PasswordResets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            )
        """)
        
        # Add two_factor_enabled column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE Users ADD COLUMN two_factor_enabled INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        conn.commit()
        conn.close()
        
        print(f"✅ Database initialized successfully at {db_path}")
        return True
    
    except sqlite3.Error as e:
        print(f"❌ Database initialization error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during database initialization: {e}")
        return False


# User-related database operations
class UserDatabase:
    """User database operations"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        """Initialize with DatabaseManager instance"""
        self.db = db_manager or DatabaseManager()
    
    def create_user(self, username: str, email: str, password_hash: str) -> Optional[int]:
        """
        Create a new user
        
        Args:
            username: User's username (unique)
            email: User's email (unique)
            password_hash: Hashed password
        
        Returns:
            user_id if successful, None if failed
        """
        query = """
            INSERT INTO Users (username, email, password_hash)
            VALUES (?, ?, ?)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (username, email, password_hash))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            return None

    # Password reset related helpers
    def create_password_reset(self, user_id: int, token: str, expires_at: str) -> Optional[int]:
        """Create a password reset token for a user"""
        query = """
            INSERT INTO PasswordResets (user_id, token, expires_at)
            VALUES (?, ?, ?)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (user_id, token, expires_at))
            conn.commit()
            pr_id = cursor.lastrowid
            conn.close()
            return pr_id
        except sqlite3.IntegrityError:
            return None

    def get_password_reset(self, token: str) -> Optional[Dict]:
        """Get password reset record by token"""
        query = "SELECT * FROM PasswordResets WHERE token = ?"
        results = self.db.execute_query(query, (token,))
        if results:
            row = results[0]
            return {
                'id': row[0],
                'user_id': row[1],
                'token': row[2],
                'expires_at': row[3],
                'used': row[4],
                'created_at': row[5]
            }
        return None

    def mark_password_reset_used(self, token: str) -> bool:
        query = "UPDATE PasswordResets SET used = 1 WHERE token = ?"
        return self.db.execute_update(query, (token,)) > 0

    def update_password_hash(self, user_id: int, new_password_hash: str) -> bool:
        """Update user's password hash"""
        query = "UPDATE Users SET password_hash = ? WHERE user_id = ?"
        return self.db.execute_update(query, (new_password_hash, user_id)) > 0
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        query = "SELECT * FROM Users WHERE email = ?"
        results = self.db.execute_query(query, (email,))
        if results:
            return self._format_user(results[0])
        return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        query = "SELECT * FROM Users WHERE username = ?"
        results = self.db.execute_query(query, (username,))
        if results:
            return self._format_user(results[0])
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by user_id"""
        query = "SELECT * FROM Users WHERE user_id = ?"
        results = self.db.execute_query(query, (user_id,))
        if results:
            return self._format_user(results[0])
        return None
    
    def update_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp"""
        query = "UPDATE Users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?"
        return self.db.execute_update(query, (user_id,)) > 0
    
    def reset_failed_attempts(self, user_id: int) -> bool:
        """Reset failed login attempts for a user"""
        query = "UPDATE Users SET failed_attempts = 0 WHERE user_id = ?"
        return self.db.execute_update(query, (user_id,)) > 0
    
    def increment_failed_attempts(self, user_id: int) -> bool:
        """Increment failed login attempts for a user"""
        query = "UPDATE Users SET failed_attempts = failed_attempts + 1 WHERE user_id = ?"
        return self.db.execute_update(query, (user_id,)) > 0
    
    @staticmethod
    def _format_user(row: Tuple) -> Dict:
        """Format user row to dictionary"""
        return {
            'user_id': row[0],
            'username': row[1],
            'email': row[2],
            'password_hash': row[3],
            'created_at': row[4],
            'last_login': row[5],
            'failed_attempts': row[6]
        }


# Transaction-related database operations
class TransactionDatabase:
    """Transaction database operations"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        """Initialize with DatabaseManager instance"""
        self.db = db_manager or DatabaseManager()
    
    def create_transaction(self, user_id: int, order_id: str = None, 
                         payment_id: str = None, amount: float = None, 
                         status: str = None) -> Optional[int]:
        """
        Create a new transaction
        
        Args:
            user_id: User's ID
            order_id: Order ID
            payment_id: Payment ID from payment gateway
            amount: Transaction amount
            status: Transaction status (pending, completed, failed, etc.)
        
        Returns:
            transaction_id if successful, None if failed
        """
        query = """
            INSERT INTO Transactions (user_id, order_id, payment_id, amount, status)
            VALUES (?, ?, ?, ?, ?)
        """
        try:
            return self.db.execute_update(query, (user_id, order_id, payment_id, amount, status))
        except sqlite3.Error:
            return None
    
    def get_transaction(self, transaction_id: int) -> Optional[Dict]:
        """Get transaction by ID"""
        query = "SELECT * FROM Transactions WHERE transaction_id = ?"
        results = self.db.execute_query(query, (transaction_id,))
        if results:
            return self._format_transaction(results[0])
        return None
    
    def get_user_transactions(self, user_id: int) -> List[Dict]:
        """Get all transactions for a user"""
        query = "SELECT * FROM Transactions WHERE user_id = ? ORDER BY transaction_date DESC"
        results = self.db.execute_query(query, (user_id,))
        return [self._format_transaction(row) for row in results]
    
    def update_transaction_status(self, transaction_id: int, status: str) -> bool:
        """Update transaction status"""
        query = "UPDATE Transactions SET status = ? WHERE transaction_id = ?"
        return self.db.execute_update(query, (status, transaction_id)) > 0
    
    @staticmethod
    def _format_transaction(row: Tuple) -> Dict:
        """Format transaction row to dictionary"""
        return {
            'transaction_id': row[0],
            'user_id': row[1],
            'order_id': row[2],
            'payment_id': row[3],
            'amount': row[4],
            'status': row[5],
            'transaction_date': row[6]
        }


# Image History-related database operations
class ImageHistoryDatabase:
    """Image history database operations"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        """Initialize with DatabaseManager instance"""
        self.db = db_manager or DatabaseManager()
    
    def create_image_record(self, user_id: int, original_image_path: str,
                           processed_image_path: str = None, style_applied: str = None,
                           payment_status: str = None) -> Optional[int]:
        """
        Create a new image history record
        
        Args:
            user_id: User's ID
            original_image_path: Path to original image
            processed_image_path: Path to processed image
            style_applied: Style name applied
            payment_status: Payment status (paid, pending, free, etc.)
        
        Returns:
            image_id if successful, None if failed
        """
        query = """
            INSERT INTO ImageHistory 
            (user_id, original_image_path, processed_image_path, style_applied, payment_status)
            VALUES (?, ?, ?, ?, ?)
        """
        try:
            return self.db.execute_update(query, 
                                        (user_id, original_image_path, processed_image_path, 
                                         style_applied, payment_status))
        except sqlite3.Error:
            return None
    
    def get_image_record(self, image_id: int) -> Optional[Dict]:
        """Get image record by ID"""
        query = "SELECT * FROM ImageHistory WHERE image_id = ?"
        results = self.db.execute_query(query, (image_id,))
        if results:
            return self._format_image(results[0])
        return None
    
    def get_user_images(self, user_id: int) -> List[Dict]:
        """Get all image records for a user"""
        query = "SELECT * FROM ImageHistory WHERE user_id = ? ORDER BY processing_date DESC"
        results = self.db.execute_query(query, (user_id,))
        return [self._format_image(row) for row in results]
    
    def update_processed_image_path(self, image_id: int, processed_image_path: str) -> bool:
        """Update processed image path"""
        query = "UPDATE ImageHistory SET processed_image_path = ? WHERE image_id = ?"
        return self.db.execute_update(query, (processed_image_path, image_id)) > 0
    
    def update_payment_status(self, image_id: int, payment_status: str) -> bool:
        """Update payment status"""
        query = "UPDATE ImageHistory SET payment_status = ? WHERE image_id = ?"
        return self.db.execute_update(query, (payment_status, image_id)) > 0
    
    @staticmethod
    def _format_image(row: Tuple) -> Dict:
        """Format image record row to dictionary"""
        return {
            'image_id': row[0],
            'user_id': row[1],
            'original_image_path': row[2],
            'processed_image_path': row[3],
            'style_applied': row[4],
            'processing_date': row[5],
            'payment_status': row[6]
        }


# Initialize database on module import
if __name__ == "__main__":
    initialize_database()
    print("Database module initialized successfully")
