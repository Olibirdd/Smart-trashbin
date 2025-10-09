import sqlite3
import os
import random
import string

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "sbvm_wifi.db")

def generate_voucher(prefix="DJM", length=4):
    """Generate a random voucher code with given prefix and length."""
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=length))
    return f"{prefix}{random_part}"

def store_voucher_in_db(code):
    """Insert voucher code into the database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO vouchers (voucher_code, redeemed, redeemed_by, redeemed_at) VALUES (?, 0, NULL, NULL)",
            (code,)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def generate_and_store_voucher(duration ):
    """Generate a unique voucher and store it in DB."""
    for _ in range(10):
        code = generate_voucher()
        if store_voucher_in_db(code):
            return code
    return None
