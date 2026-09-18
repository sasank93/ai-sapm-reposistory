import sqlite3
import os
from datetime import datetime

# Get the absolute path of the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'spam_guard.db')

def init_db():
    """Initialize the SQLite database and create the scan_history table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id TEXT,
            subject TEXT,
            verdict TEXT,
            timestamp DATETIME,
            user_email TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_scan_result(email_id, subject, verdict, user_email):
    """Saves a single email classification result to the history table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO scan_history (email_id, subject, verdict, timestamp, user_email)
        VALUES (?, ?, ?, ?, ?)
    ''', (email_id, subject, verdict, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_email))
    conn.commit()
    conn.close()

def get_history():
    """Retrieves all scan records from the history table."""
    conn = sqlite3.connect(DB_PATH)
    # Using pandas to read the SQL query directly into a DataFrame
    import pandas as pd
    df = pd.read_sql_query("SELECT * FROM scan_history ORDER BY timestamp DESC", conn)
    conn.close()
    return df

def clear_history():
    """Deletes all records from the history table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scan_history")
    conn.commit()
    conn.close()
