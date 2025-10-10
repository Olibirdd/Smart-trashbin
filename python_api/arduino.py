import serial
import time

# Replace with your Arduino COM port
# On Windows: something like "COM3"
# On Linux/Raspberry Pi: "/dev/ttyUSB0" or "/dev/ttyACM0"
PORT = "COM4"
BAUD = 9600

def main():
    try:
        # Open serial connection
        ser = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(2)  # wait for Arduino to reset

        while True:
            # Ask user for a message
            msg = input("Enter message for Arduino LCD: ")
            if not msg:
                continue
            ser.write((msg + "\n").encode("utf-8"))
            print(f"Sent: {msg}")

    except serial.SerialException as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
