from time import sleep
import paho.mqtt.client as mqtt
from models import VitaleTegn, db
from flask import current_app

mqtt_local_broker = "20.0.194.60"
mqtt_local_topic = "sundhed/data"
mqtt_local_user = "Plejehjem1"
mqtt_local_pass = "P987lejehjem1."

def send_email(alert_type, numbers):
    # Implement your email logic here
    print(f"Sending email with type: {alert_type}, numbers: {numbers}")

def on_message(client, userdata, message):
    try:
        msg_str = message.payload.decode("utf-8").strip()
        print(f"Received message: {msg_str}")
        
        if msg_str.startswith("HELP:"):
            # Extract the numbers after "HELP:"
            numbers = msg_str.split("HELP:")[1].strip()
            print(f"Extracted numbers: {numbers}")
            send_email("HELP", numbers)

        elif msg_str.startswith("FALD:"):
            numbers = msg_str.split("FALD:")[1].strip()
            print(f"Extracted numbers: {numbers}")
            send_email("FALD", numbers)

        elif msg_str.startswith("PULS"):
            # Split the message string by ":"
            parts = msg_str.split(":")
            
            if len(parts) == 4:
                header = parts[0]   # "PULS"
                cpr = parts[1].strip()
                pulse = parts[2].strip()
                battery = parts[3].strip()
                
                print(f"Header: {header} / CPR: {cpr} / Pulse: {pulse} / Battery: {battery}")
                
                # Insert the data into the database
                try:
                    VitaleTegn.insert_data(cpr, pulse, battery)
                    print("Data inserted successfully")
                except Exception as e:
                    print(f"Error inserting data: {e}")
            else:
                print("Invalid PULS message format.")

        # Add more handlers as needed for other message types

    except Exception as e:
        print(f"Error processing message: {e}")
    finally:
        sleep(0.5)

def start_logging():
    client = mqtt.Client()
    client.username_pw_set(mqtt_local_user, mqtt_local_pass)
    client.on_message = on_message

    client.connect(mqtt_local_broker, 1883, 60)
    client.subscribe(mqtt_local_topic)
    client.loop_start()

    print("Listening for messages on local broker...")
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        print("\nProgram stopped by the user")
    finally:
        client.loop_stop()
        client.disconnect()
