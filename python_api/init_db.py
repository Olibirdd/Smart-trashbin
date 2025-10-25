import sqlite3
import os
from datetime import datetime, timedelta
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "sbvm_wifi.db")

MAX_MACS = 10

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


def check_mac_count():
    if not os.path.exists(DATABASE):
        print("❌ Database not found! Please run init_db.py first.")
        return

    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Count unique MAC addresses
        cursor.execute("SELECT COUNT(DISTINCT mac_address) FROM access_time")
        count = cursor.fetchone()[0]

        print(f"📊 Current unique MAC addresses: {count}")

        if count >= MAX_MACS:
            print("⚠️  Maximum number of unique MAC addresses reached (10)!")
        else:
            print(f"✅  You can still add {MAX_MACS - count} more MAC addresses.")

    except sqlite3.Error as e:
        print("Database error:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()

