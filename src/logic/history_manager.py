# src/logic/history_manager.py
# -- لإدارة قاعدة بيانات SQLite الخاصة بالسجل --
# Purpose: Manages the SQLite database for history entries.

import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# --- Constants ---
DB_FILENAME = "advanced_downloader_history.db"
TABLE_NAME = "history"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S" # تنسيق أكثر قابلية للقراءة من ISO

class HistoryManager:
    """يدير عمليات قاعدة بيانات SQLite لتخزين واسترجاع سجل الاستخدام."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initializes the HistoryManager and connects to the database.
        Creates the history table if it doesn't exist.

        Args:
            db_path (Optional[Path]): Path to the database file. If None,
                                      it defaults to the directory of the main script/executable.
        """
        if db_path is None:
            db_path = self._get_default_db_path()

        self.db_path: Path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        print(f"HistoryManager: Using database at: {self.db_path}")

        try:
            # Ensure the directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self._create_table()
        except sqlite3.Error as e:
            print(f"HistoryManager Error: Could not connect or initialize database: {e}")
            # Consider raising an exception or handling this more gracefully
            self.conn = None
            self.cursor = None
        except OSError as e:
            print(f"HistoryManager Error: Could not create database directory: {e}")
            self.conn = None
            self.cursor = None

    def _get_default_db_path(self) -> Path:
        """Determines the default path for the database file."""
        try:
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                # Running as a PyInstaller bundle
                base_path = Path(sys.executable).parent
            elif getattr(sys, 'frozen', False):
                 # Running as a bundled executable (e.g., pyinstaller --onefile)
                 base_path = Path(sys.executable).parent
            else:
                # Running as a script - path of main.py
                # Assuming main.py is in the project root
                base_path = Path(__file__).resolve().parent.parent.parent # project root
        except Exception as e:
            print(f"HistoryManager Warning: Could not determine base path: {e}. Using current directory.")
            base_path = Path(".")
        return base_path / DB_FILENAME


    def _create_table(self) -> None:
        """Creates the history table if it doesn't exist."""
        if not self.cursor:
            print("HistoryManager Error: No cursor available for table creation.")
            return
        try:
            self.cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT,
                    timestamp TEXT NOT NULL,
                    operation_type TEXT NOT NULL
                )
            ''')
            self.conn.commit() # type: ignore
            print(f"HistoryManager: Table '{TABLE_NAME}' checked/created successfully.")
        except sqlite3.Error as e:
            print(f"HistoryManager Error: Could not create table '{TABLE_NAME}': {e}")

    def add_entry(self, url: str, title: Optional[str], operation_type: str) -> bool:
        """
        Adds a new entry to the history database.

        Args:
            url (str): The URL used.
            title (Optional[str]): The title associated with the URL (if available).
            operation_type (str): The type of operation performed (e.g., 'Download', 'Fetch Info', 'Get Links').

        Returns:
            bool: True if the entry was added successfully, False otherwise.
        """
        if not self.conn or not self.cursor:
            print("HistoryManager Error: Database connection not available for adding entry.")
            return False

        current_timestamp: str = datetime.now().strftime(DATE_FORMAT)
        sql = f'''INSERT INTO {TABLE_NAME} (url, title, timestamp, operation_type)
                  VALUES (?, ?, ?, ?)'''
        try:
            print(f"HistoryManager: Adding entry - URL: {url}, Title: {title}, Type: {operation_type}")
            self.cursor.execute(sql, (url, title, current_timestamp, operation_type))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"HistoryManager Error: Could not add entry: {e}")
            return False

    def get_all_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves recent history entries, ordered by timestamp descending.

        Args:
            limit (int): The maximum number of entries to retrieve.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                                 represents a history entry. Returns empty list on error.
        """
        if not self.cursor:
            print("HistoryManager Error: No cursor available for fetching entries.")
            return []

        sql = f'''SELECT id, url, title, timestamp, operation_type
                  FROM {TABLE_NAME}
                  ORDER BY timestamp DESC
                  LIMIT ?'''
        try:
            self.cursor.execute(sql, (limit,))
            rows = self.cursor.fetchall()
            # Convert rows (tuples) to list of dictionaries
            entries = [
                {
                    "id": row[0],
                    "url": row[1],
                    "title": row[2],
                    "timestamp": row[3],
                    "operation_type": row[4],
                }
                for row in rows
            ]
            # print(f"HistoryManager: Fetched {len(entries)} entries.") # Debug: Can be verbose
            return entries
        except sqlite3.Error as e:
            print(f"HistoryManager Error: Could not fetch entries: {e}")
            return []

    def delete_entry(self, entry_id: int) -> bool:
        """
        Deletes a specific entry from the history database by its ID.

        Args:
            entry_id (int): The ID of the entry to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        if not self.conn or not self.cursor:
            print("HistoryManager Error: Database connection not available for deleting entry.")
            return False

        sql = f'DELETE FROM {TABLE_NAME} WHERE id = ?'
        try:
            print(f"HistoryManager: Deleting entry with ID: {entry_id}")
            self.cursor.execute(sql, (entry_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0 # Check if any row was actually deleted
        except sqlite3.Error as e:
            print(f"HistoryManager Error: Could not delete entry {entry_id}: {e}")
            return False

    def clear_all_entries(self) -> bool:
        """
        Deletes all entries from the history table.

        Returns:
            bool: True if clearing was successful, False otherwise.
        """
        if not self.conn or not self.cursor:
            print("HistoryManager Error: Database connection not available for clearing history.")
            return False

        sql = f'DELETE FROM {TABLE_NAME}'
        try:
            print("HistoryManager: Clearing all history entries.")
            self.cursor.execute(sql)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"HistoryManager Error: Could not clear history: {e}")
            return False

    def close_db(self) -> None:
        """Closes the database connection."""
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
                self.cursor = None
                print("HistoryManager: Database connection closed.")
            except sqlite3.Error as e:
                print(f"HistoryManager Error: Could not close database connection: {e}")

    def __del__(self):
        """Ensure database connection is closed when the object is destroyed."""
        self.close_db()