import time
import serial
import os
import threading, time, subprocess
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
import random
import pymongo
from pymongo import MongoClient
import django
import certifi
#import dns.resolver
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from gen_voucher import generate_and_store_voucher
from init_db import init_db




# ----------------------------
# Django setup
# ----------------------------
#dns.resolver.default_resolver = #dns.resolver.Resolver(configure=False)
#dns.resolver.default_resolver.nameservers = ['8.8.8.8','8.8.4.4']
if not settings.configured:
    settings.configure(
        PASSWORD_HASHERS=[
            'django.contrib.auth.hashers.PBKDF2PasswordHasher',  # default in Django
        ],
        SECRET_KEY='some-random-secret-key',  # Django requires a SECRET_KEY
    )
django.setup()

# ----------------------------
# Init Flask
# ----------------------------
app = Flask(__name__)
CORS(app)

# ----------------------------
# Init SQLite
# ----------------------------
init_db()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "sbvm_wifi.db")
REMOVE_SCRIPT = os.path.join(BASE_DIR, "actions", "remove_mac.sh")
ALLOW_SCRIPT = os.path.join(BASE_DIR, "actions", "allow_mac.sh")
API_KEY = "DJMSBVMPROJ2025"

client = MongoClient(
    "mongodb://smart_bin_wifi:smart_bin_wifi@"
    "ac-kfese88-shard-00-00.9fjmqox.mongodb.net:27017,"
    "ac-kfese88-shard-00-01.9fjmqox.mongodb.net:27017,"
    "ac-kfese88-shard-00-02.9fjmqox.mongodb.net:27017/"
    "?ssl=true&replicaSet=atlas-ce5so5-shard-0&authSource=admin&retryWrites=true&w=majority"
)

# Select database and collections
mdb = client["smart_vending"]
users_col = mdb["users"]
vouchers_col = mdb["vouchers"]
logs_col = mdb["activity_logs"]

# Test connection
try:
    client.admin.command("ping")
    print("MongoDB connection successful")
except Exception as e:
    print(f"MongoDB connection failed: {e}")

# Arduino Script
def arduino_listener(serial_port='/dev/ttyACM0', baudrate=9600):
    try:
        arduino = serial.Serial(serial_port, baudrate, timeout=1)
        print(f'Listening to Arduino on {serial_port}')
        time.sleep(2)
    except Exception as e:
        print(f'Could not open serial port {serial_port}: {e}')
        return

    while True:
        try:
            line = arduino.readline().decode('utf-8').strip()
            if line:
                print(f": {line}")
                if line.startswith("BOTTLE_COUNT:"):
                    try:
                        count = int(line.split(":")[1])
                        minutes = count * 5

                        voucher = generate_and_store_voucher(duration=minutes)
                        if voucher:
                            print(f'Voucher Generated: {voucher}, Duration: {minutes} mins')
                            arduino.write((voucher + "\n").encode('utf-8'))
                        else:
                            print("Failed to generate voucher")
                    except Exception as e:
                        print(f"Invalid count format: {e}")
        except Exception as e:
            print(f'Error reading from Arduino: {e}')
        time.sleep(0.1)

listener_thread = threading.Thread(target=arduino_listener, daemon=True)
listener_thread.start()

@app.route("/")
def index():
    return "Hello"

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
    hashed_pw = make_password(password)
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
# API: Leaderboard
# ----------------------------
@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    """
    Returns a leaderboard of users based on total voucher_duration,
    grouped by redeemed_by_email. Also calculates total bottles = total_duration / 5.
    """
    try:
        # MongoDB aggregation pipeline
        pipeline = [
            {"$match": {"redeemed": True, "redeemed_by_email": {"$ne": None}}},
            {
                "$group": {
                    "_id": "$redeemed_by_email",
                    "total_duration": {"$sum": "$voucher_duration"}
                }
            },
            {"$sort": {"total_duration": -1}},
            {"$limit": 10}
        ]

        results = list(vouchers_col.aggregate(pipeline))

        leaderboard = []
        for r in results:
            email = r.get("_id")
            total_duration = r.get("total_duration", 0)
            bottle_count = total_duration / 5 if total_duration else 0

            # Optional: get username
            user = users_col.find_one({"email": email})
            username = user.get("username") if user else email

            leaderboard.append({
                "username": username,
                "email": email,
                "total_duration": total_duration,
                "bottle_count": round(bottle_count, 2)
            })

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        print(f"❌ Error generating leaderboard: {e}")
        return jsonify({"error": "Failed to generate leaderboard"}), 500


# ----------------------------
# Helper functions
# ----------------------------
def get_mac_from_ip(ip):
    # Attempt to retrieve the MAC address of a given IP
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
def generate_voucher_code():
    """Generate a 6-character voucher with randomized prefix letters and 3 digits."""
    base_prefix = random.choice(['JDM', 'AMF'])
    # Randomize the order of letters in the prefix
    prefix = ''.join(random.sample(base_prefix, len(base_prefix)))
    # Add 3 random digits
    digits = ''.join(random.choices('0123456789', k=3))
    return f"{prefix}{digits}"

def generate_and_store_voucher(duration, max_attempts=10):
    """Generate a unique voucher and store it in MongoDB with duration (minutes)."""
    for _ in range(max_attempts):
        code = generate_voucher_code()
        if not vouchers_col.find_one({"voucher_code": code}):
            now = datetime.utcnow()
            vouchers_col.insert_one({
                "voucher_code": code,
                "voucher_duration": duration,  
                "redeemed": False,
                "redeemed_by_email": None,
                "created_at": now
            })
            return code
    return None


def generate_voucher_endpoint():
    code = generate_and_store_voucher()
    if code:
        return jsonify({
            "voucher": code,
            "redeemed": False,
            "redeemed_by_email": None,
            "message": "Voucher generated successfully"
        }), 200
    else:
        return jsonify({"error": "Failed to generate a unique voucher"}), 500
# ----------------------------
# API: Redeem Voucher
# ----------------------------
@app.route('/api/test', methods=['POST'])
def test():
    return jsonify({"success": True,"message": "ok"})
    
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import sqlite3, subprocess

@app.route('/api/redeem', methods=['POST'])
def redeem():
    data = request.get_json()
    voucher = data.get('voucher')
    email = data.get('email') 

    now = datetime.utcnow()  # Use UTC for MongoDB timestamps

    # --- MongoDB: Check if user exists ---
    user = users_col.find_one({"email": email})
    if not user:
        return jsonify({'error': 'Account not found. Please create an account.'}), 400

    # --- MongoDB: Check voucher exists and not redeemed ---
    voucher_doc = vouchers_col.find_one({"voucher_code": voucher})
    if not voucher_doc:
        return jsonify({'error': 'Invalid voucher'}), 400
    elif voucher_doc.get("redeemed", False):
        return jsonify({'error': 'Voucher already redeemed'}), 400

    # ✅ Use voucher_duration from MongoDB
    duration_minutes = voucher_doc.get("voucher_duration", 5)  # fallback = 5 mins

    # --- SQLite: Handle MAC and access control ---
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    client_ip = request.headers.get('X-Real-IP', request.remote_addr)
    mac = "00:11:22:33:44:55" if client_ip == "127.0.0.1" else get_mac_from_ip(client_ip)
    if not mac:
        conn.close()
        return jsonify({'error': 'Could not determine MAC address'}), 400

    cursor.execute("SELECT expires, active FROM access_time WHERE mac_address = ?", (mac,))
    row = cursor.fetchone()

    if row:
        current_expiry_str, active = row
        if active == 1:
            # MAC is active → extend expiry by voucher_duration
            current_expiry_dt = datetime.strptime(current_expiry_str, "%Y-%m-%d %H:%M:%S.%f")
            new_expiry = current_expiry_dt + timedelta(minutes=duration_minutes)
            cursor.execute(
                "UPDATE access_time SET expires=? WHERE mac_address=?",
                (new_expiry, mac)
            )
            message = f"Enjoy your extra {duration_minutes} minutes of internet service."
        else:
            # MAC exists but inactive → set active=1, expiry = now + duration
            try:
                subprocess.run(["sudo", ALLOW_SCRIPT, mac], check=True)
            except subprocess.CalledProcessError:
                conn.close()
                return jsonify({'error': 'Failed to whitelist MAC address'}), 500

            new_expiry = datetime.now() + timedelta(minutes=duration_minutes)
            cursor.execute(
                "UPDATE access_time SET expires=?, active=1 WHERE mac_address=?",
                (new_expiry, mac)
            )
            message = f"Voucher redeemed. MAC {mac} whitelisted until {new_expiry.strftime('%H:%M:%S')} ({duration_minutes} mins)"
    else:
        # MAC not in SQLite → insert with active=1, expiry = now + duration
        try:
            subprocess.run(["sudo", ALLOW_SCRIPT, mac], check=True)
        except subprocess.CalledProcessError:
            conn.close()
            return jsonify({'error': 'Failed to whitelist MAC address'}), 500

        new_expiry = datetime.now() + timedelta(minutes=duration_minutes)
        cursor.execute(
            "INSERT INTO access_time (mac_address, ip_address, expires, active) VALUES (?, ?, ?, ?)",
            (mac, client_ip, new_expiry, 1)
        )
        message = f"Voucher redeemed. MAC {mac} whitelisted until {new_expiry.strftime('%H:%M:%S')} ({duration_minutes} mins)"

    conn.commit()
    conn.close()

    # --- MongoDB: Mark voucher as redeemed ---
    vouchers_col.update_one(
        {"voucher_code": voucher},
        {"$set": {
            "redeemed": True,
            "redeemed_by_email": email,
            "redeemed_at": now
        }}
    )

    # --- MongoDB: Log voucher redemption ---
    logs_col.insert_one({
        "action": "redeem",
        "voucher_code": voucher,
        "email": email,
        "timestamp": now,
        "duration": duration_minutes
    })

    # --- Try to nudge client ---
    try:
        subprocess.run(["curl", "-s", f"http://{client_ip}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Could not nudge client: {e}")

    return jsonify({'message': message, 'duration': duration_minutes})


# ----------------------------
# API: Delete Voucher
# ----------------------------
def voucher_cleaner():
    """Delete vouchers older than 3 days that are still unredeemed."""
    while True:
        try:
            time.sleep(3600)  # run every hour
            now = datetime.utcnow()
            threshold = now - timedelta(days=3)
            print("Checking for unredeemed vouchers older than 3 days...")
            # Delete unredeemed vouchers older than 3 days
            result = vouchers_col.delete_many({
                "redeemed": False,
                "created_at": {"$lt": threshold}
            })

            if result.deleted_count > 0:
                print(f"🧹 Deleted {result.deleted_count} expired unredeemed vouchers (older than 3 days).")
        except Exception as e:
            print(f"❌ Voucher cleaner error: {e}")


# ----------------------------
# Expiry Watcher (SQLite only)
# ----------------------------
def expiry_watcher():
    while True:
        time.sleep(60)
        now = datetime.now()
        conn = sqlite3.connect('sbvm_wifi.db')
        cur = conn.cursor()

        # Only select active entries
        cur.execute("SELECT mac_address, ip_address, expires FROM access_time WHERE active=1")
        rows = cur.fetchall()
        # print(f"Checking {len(rows)} active entries for expiry at {now}")
        print("Checking for expired access")

        for mac, ip, exp_str in rows:
            expiry = datetime.fromisoformat(exp_str)
            if expiry <= now:
                try:
                    subprocess.run(["sudo", REMOVE_SCRIPT, mac], check=True)
                    print(f"Removed MAC {mac}")
                except subprocess.CalledProcessError as e:
                    print(f"Failed to remove MAC {mac}: {e}")

                # Set active to 0 instead of deleting
                cur.execute("UPDATE access_time SET active=0 WHERE mac_address=?", (mac,))

        conn.commit()
        conn.close()
# ----------------------------
# Main
# ----------------------------
if __name__ == '__main__':
    threading.Thread(target=expiry_watcher, daemon=True).start()
    threading.Thread(target=voucher_cleaner, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)               
                

