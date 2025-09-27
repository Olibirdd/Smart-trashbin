import os
import threading, time, subprocess
from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, timedelta
from gen_voucher import generate_and_store_voucher
from init_db import init_db
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from flask_cors import CORS




# ----------------------------
# Init SQLite
# ----------------------------
init_db()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "sbvm_wifi.db")
REMOVE_SCRIPT = os.path.join(BASE_DIR, "actions", "remove_mac.sh")
ALLOW_SCRIPT = os.path.join(BASE_DIR, "actions", "allow_mac.sh")

ACCESS_DURATION_MINUTES = 5
API_KEY = "DJMSBVMPROJ2025"


# ----------------------------
# Init MongoDB
# ----------------------------
client = MongoClient("mongodb+srv://smart_bin_wifi:smart_bin_wifi@cluster0.9fjmqox.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")   # change if using Atlas
mdb = client["smart_vending"]

users_col = mdb["users"]
vouchers_col = mdb["vouchers"]
logs_col = mdb["activity_logs"]


app = Flask(__name__)
CORS(app)


# ----------------------------
# API: Register User (MongoDB)
# ----------------------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirmPassword")

    # Basic validations
    if not username or not email or not password or not confirm_password:
        return jsonify({"error": "All fields are required"}), 400

    if password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400

    # Check if email already exists
    existing_user = users_col.find_one({"email": email})
    if existing_user:
        return jsonify({"error": "Email already registered"}), 400

    # Save user (hash password for security)
    hashed_pw = generate_password_hash(password)
    user_doc = {
        "username": username,
        "email": email,
        "password": hashed_pw,
        "role": "user",
        "created_at": datetime.now()
    }
    users_col.insert_one(user_doc)

    return jsonify({"message": "Account successfully created"}), 201


# ----------------------------
# Helper functions
# ----------------------------
def get_mac_from_ip(ip):
    try:
        subprocess.run(['ping', '-c', '1', '-W', '1', ip],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        with open('/proc/net/arp', 'r') as arp_table:
            lines = arp_table.readlines()[1:]
            for line in lines:
                parts = line.split()
                if parts[0] == ip and parts[3] != "00:00:00:00:00:00":
                    return parts[3].lower()
    except Exception as e:
        print(f"Error retrieving MAC for IP {ip}: {e}")
    return None


# ----------------------------
# API: Generate Voucher
# ----------------------------
@app.route('/api/generate_voucher', methods=['POST'])
def generate_voucher_endpoint():
    key = request.headers.get("X-API-KEY")
    if key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    code = generate_and_store_voucher()
    if code:
        return jsonify({"voucher": code, "message": "Voucher generated successfully"}), 200
    else:
        return jsonify({"error": "Failed to generate a unique voucher"}), 500


# ----------------------------
# API: Redeem Voucher
# ----------------------------
@app.route('/api/redeem', methods=['POST'])
def redeem():
    data = request.get_json()
    voucher = data.get('voucher')
    email = data.get('email') 

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    user = users_col.find_one({"email": email})  # assuming users_col is your MongoDB users collection
    if not user:
        return jsonify({'error': 'Account not found. Please create an account.'}), 400

    # Check voucher validity in SQLite
    cursor.execute("SELECT redeemed FROM vouchers WHERE voucher_code = ?", (voucher,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Invalid voucher'}), 400
    if row[0]:
        conn.close()
        return jsonify({'error': 'Voucher already redeemed'}), 400

    client_ip = request.headers.get('X-Real-IP', request.remote_addr)
    if client_ip == "127.0.0.1":
        mac = "00:11:22:33:44:55"
    else:
        mac = get_mac_from_ip(client_ip)
    if not mac:
        conn.close()
        return jsonify({'error': 'Could not determine MAC address'}), 400

    now = datetime.now()

    # --- SQLite: Handle Access Control ---
    cursor.execute("SELECT expires FROM access_time WHERE mac_address = ?", (mac,))
    row = cursor.fetchone()
    if row:
        current_expiry = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f")
        new_expiry = max(now, current_expiry) + timedelta(minutes=ACCESS_DURATION_MINUTES)
        cursor.execute("UPDATE access_time SET expires=? WHERE mac_address=?", (new_expiry, mac))
        message = "Enjoy your extra 5 minutes of internet service."
    else:
        # try:
        #     subprocess.run(["sudo", ALLOW_SCRIPT, mac], check=True)
        # except subprocess.CalledProcessError as e:
        #     conn.close()
        #     return jsonify({'error': 'Failed to whitelist MAC address'}), 500

        new_expiry = now + timedelta(minutes=ACCESS_DURATION_MINUTES)
        cursor.execute(
            "INSERT INTO access_time (mac_address, ip_address, expires) VALUES (?, ?, ?)",
            (mac, client_ip, new_expiry)
        )
        message = f"Voucher redeemed. MAC {mac} whitelisted until {new_expiry.strftime('%H:%M:%S')}"

    # Mark voucher as redeemed in SQLite
    cursor.execute(
        "UPDATE vouchers SET redeemed = 1, redeemed_by = ?, redeemed_at = ? WHERE voucher_code = ?",
        (mac, now, voucher)
    )
    conn.commit()
    conn.close()

    # --- MongoDB: Log voucher redemption ---
    vouchers_col.update_one(
        {"voucher_code": voucher},
        {"$set": {
            "redeemed": True,
            "redeemed_by_email": email,   
            "redeemed_at": now
        }}
    )

    logs_col.insert_one({
        "action": "redeem",
        "voucher_code": voucher,
        "email": email,
        "timestamp": now
    })

    # Try to nudge client
    try:
        subprocess.run(["curl", "-s", f"http://{client_ip}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Could not nudge client: {e}")

    return jsonify({'message': message})


# ----------------------------
# Expiry Watcher (SQLite only)
# ----------------------------
def expiry_watcher():
    while True:
        time.sleep(60)
        now = datetime.now()
        conn = sqlite3.connect('sbvm_wifi.db')
        cur = conn.cursor()
        cur.execute("SELECT mac_address, ip_address, expires FROM access_time")
        rows = cur.fetchall()
        print(f"Checking {len(rows)} entries for expiry at {now}")
        for mac, ip, exp_str in rows:
            expiry = datetime.fromisoformat(exp_str)
            if expiry <= now:
                subprocess.run(["sudo", REMOVE_SCRIPT, mac], check=True)
                cur.execute("DELETE FROM access_time WHERE mac_address=?", (mac,))
        conn.commit()
        conn.close()


if __name__ == '__main__':
    threading.Thread(target=expiry_watcher, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
