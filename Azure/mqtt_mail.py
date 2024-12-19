# mqtt_listener/mqtt_mail.py

from time import sleep
from datetime import datetime
import paho.mqtt.client as mqtt
from flask import current_app
from app import app  # Import the Flask app instance
from models import db, VitaleTegn
from encryption import encrypt_data, decrypt_data
from mqtt_listener import send_email  # Adjust the import path as needed
import pytz

# MQTT Configuration
MQTT_LOCAL_BROKER = "20.0.194.60"
MQTT_LOCAL_TOPIC = "sundhed/data"
MQTT_LOCAL_USER = "Plejehjem1"
MQTT_LOCAL_PASS = "P987lejehjem1."

def insert_data(cpr, pulse, battery):
    with app.app_context():  # Ensure operations occur within the Flask app context
        try:
            # Encrypt the data before insertion
            encrypted_cpr = encrypt_data(cpr)
            encrypted_pulse = encrypt_data(str(pulse))
            encrypted_battery = encrypt_data(str(battery))
            timestamp = datetime.now(pytz.timezone("Europe/Copenhagen")).strftime("%Y-%m-%d %H:%M:%S")  # Format datetime

            # Insert the encrypted data into the database
            VitaleTegn.insert_data(cpr, timestamp, pulse, battery)

            # Commit the transaction
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error inserting data: {e}")
            return False


def send_data(client, userdata, message):
    try:
        msg_str = message.payload.decode("utf-8").strip()
        print(f"Received message: {msg_str}")
        
        if msg_str.startswith("HELP:"):
            # Extract the numbers after "HELP:"
            numbers = msg_str.split("HELP:")[1].strip()
            print(f"Extracted numbers: {numbers}")
            
            # Pass the numbers to send_email()
            send_email("HELP", numbers)
            print("Help message received, sending mail with numbers")

        elif msg_str.startswith("FALD:"):
            # Extract the numbers after "FALD:"
            numbers = msg_str.split("FALD:")[1].strip()
            print(f"Extracted numbers: {numbers}")
            
            # Pass the numbers to send_email()
            send_email("FALD", numbers)
            print("Fald message received, sending mail with numbers")

        elif msg_str.startswith("PULS:"):
            # Split the message string by ":"
            parts = msg_str.split(":")
            
            # Expected format: PULS:010101-1111:69.4:99.0
            if len(parts) == 4:
                header = parts[0].strip()  # "PULS"
                cpr = parts[1].strip()      # "010101-1111"
                pulse = parts[2].strip()    # "69.4"
                battery = parts[3].strip()  # "99.0"
                
                print(f"Header: {header} / CPR: {cpr} / Pulse: {pulse} / Battery: {battery}")
                success = insert_data(cpr, pulse, battery)
                if success:
                    print("Data inserted successfully")
                else:
                    print("Failed to insert data")
            else:
                print("Invalid PULS message format.")
        else:
            print("Unknown message type received.")

    except Exception as e:
        print(f"Error processing message: {e}")
        with app.app_context():
            app.logger.error(f"Error processing message: {e}")
    
    finally:
        sleep(0.5)

def start_logging():
    """
    This function starts the MQTT logging process.
    """
    try:
        # Initialize MQTT client
        client = mqtt.Client()
        client.username_pw_set(MQTT_LOCAL_USER, MQTT_LOCAL_PASS)
        client.on_message = send_data

        # Connect to local broker
        client.connect(MQTT_LOCAL_BROKER, 1883, 60)
        
        # Subscribe to the topic on the local broker
        client.subscribe(MQTT_LOCAL_TOPIC)

        # Start listening for messages (non-blocking)
        client.loop_start()

        print("Listening for messages on local broker...")
        while True:
            sleep(1)  # Keeps the program running while listening

    except KeyboardInterrupt:
        print("\nProgram stopped by the user")
    except Exception as e:
        print(f"Error in subscribe: {e}")
        with app.app_context():
            app.logger.error(f"Error in subscribe: {e}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    start_logging()
