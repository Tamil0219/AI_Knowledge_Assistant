"""
Test Suite for Image History logging and retrieval
"""

import unittest
import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

# For our tests we don't rely on any frontend code.  We'll interact with
# the database directly via sqlite3 and the initialization logic.  This
# avoids the need to install or stub Streamlit, Razorpay, etc.

from backend.database import initialize_database


# helper not needed; we will use sqlite3.connect directly


class TestImageHistory(unittest.TestCase):
    """Basic database sanity tests for ImageHistory table."""

    def setUp(self):
        # prepare a unique temporary database file inside the database directory
        import uuid
        self.test_db = os.path.join('database', f'test_history_{uuid.uuid4().hex}.db')
        os.makedirs(os.path.dirname(self.test_db), exist_ok=True)
        # initialize the fresh file
        initialize_database(db_path=self.test_db)
        # create a dummy user so we can link history records to someone
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Users (username, email, password_hash) VALUES (?, ?, ?)"
                , ('testuser', 'test@example.com', 'hash'))
            conn.commit()

    def tearDown(self):
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except PermissionError:
                # if another process still has the file open just ignore it
                pass

    def test_migration_and_insert(self):
        """Drop the table and reinitialize to verify migration adds columns."""
        # simulate old schema without optional columns
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS ImageHistory")
        cursor.execute(
            """
            CREATE TABLE ImageHistory (
                image_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_image_path TEXT NOT NULL,
                processed_image_path TEXT,
                style_applied TEXT,
                processing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payment_status TEXT,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            )"""
        )
        conn.commit()
        conn.close()

        # re-run initialization which should add missing columns
        initialize_database(db_path=self.test_db)

        # assert that new columns are present
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(ImageHistory)")
        cols = [row[1] for row in cursor.fetchall()]
        self.assertIn('processing_time_seconds', cols)
        self.assertIn('intensity_level', cols)

        # insert a record including the new columns to ensure they accept data
        cursor.execute("SELECT user_id FROM Users WHERE username = ?", ('testuser',))
        user_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO ImageHistory (user_id, original_image_path, processed_image_path, "
            "style_applied, payment_status, processing_time_seconds, intensity_level) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)"
            , (user_id, 'a.png', 'b.png', 'TestStyle', 'free', 1.23, 'medium'))
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM ImageHistory WHERE user_id = ?", (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)


    def test_missing_columns_migration(self):
        """Simulate an old schema and verify migration adds the new columns."""
        # manually recreate table without optional fields
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS ImageHistory")
        cursor.execute(
            """
            CREATE TABLE ImageHistory (
                image_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_image_path TEXT NOT NULL,
                processed_image_path TEXT,
                style_applied TEXT,
                processing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payment_status TEXT,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            )"""
        )
        conn.commit()
        conn.close()

        # re-run initialization which should add missing columns
        initialize_database(db_path=self.test_db)

        # check that columns exist now
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(ImageHistory)")
        cols = [row[1] for row in cursor.fetchall()]
        conn.close()
        self.assertIn('processing_time_seconds', cols)
        self.assertIn('intensity_level', cols)


if __name__ == '__main__':
    unittest.main()
