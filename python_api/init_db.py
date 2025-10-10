import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "sbvm_wifi.db")

def init_db():
    # Remove existing database to reset
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
        print(f"Existing database at {DATABASE} removed.")

    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode=WAL;")

    # Create access_time table with new column 'active'
    cursor.execute("""
        CREATE TABLE access_time (
            mac_address TEXT NOT NULL PRIMARY KEY,
            ip_address TEXT,
            expires DATETIME NOT NULL,
            active INTEGER NOT NULL DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"Database initialized/reset at {DATABASE} with 'active' column.")

if __name__ == "__main__":
    init_db()

