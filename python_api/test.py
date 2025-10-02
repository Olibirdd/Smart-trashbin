import serial
import random
import string

# Configure your serial port (change COM port if needed)
arduino = serial.Serial('COM4', 9600, timeout=1)  # Windows example
# arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)  # Linux example

def generate_voucher(length=8):
    """Generate a random voucher code"""
    letters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

print("Waiting for Arduino signal...")

while True:
    line = arduino.readline().decode('utf-8').strip()
    if line:
        print(f"Received from Arduino: {line}")
        if line == "BOTTLE_DETECTED":
            voucher = generate_voucher()
            print(f"Voucher Generated: {voucher}")
