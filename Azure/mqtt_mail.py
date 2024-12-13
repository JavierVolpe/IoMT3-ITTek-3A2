from time import sleep
import paho.mqtt.client as mqtt
from mqtt_listener import send_email  # Ensure send_email accepts an argument

mqtt_local_broker  = "20.0.194.60"  
mqtt_local_topic   = "sundhed/data" 
mqtt_local_user    = "Plejehjem1"
mqtt_local_pass    = "P987lejehjem1."

# This function is triggered when a message is received from the local broker
def send_data(client, userdata, message):
    try:
        msg_str = message.payload.decode("utf-8").strip()
        print(f"Received message: {msg_str}")
        
        if msg_str.startswith("HELP:"):
            # Extract the numbers after "HELP:"
            numbers = msg_str.split("HELP:")[1].strip()
            print(f"Extracted numbers: {numbers}")
            
            # Pass the numbers to send_email()
            send_email("HELP",numbers)
            print("Help message received, sending mail with numbers")

        if msg_str.startswith("FALD:"):
            # Extract the numbers after "HELP:"
            numbers = msg_str.split("FALD:")[1].strip()
            print(f"Extracted numbers: {numbers}")
            
            # Pass the numbers to send_email()
            send_email("FALD",numbers)
            print("Fald message received, sending mail with numbers")
    
    except Exception as e:
        print(f"Error processing message: {e}")
    
    finally:
        sleep(0.5)

def start_logging():
    """
    This function starts the logging process.
    """
    try:
        # Initialize MQTT client with legacy callback API
        client = mqtt.Client(callback_api_version=1)  # Ensure paho-mqtt is updated
        client.username_pw_set(mqtt_local_user, mqtt_local_pass)
        client.on_message = send_data

        # Connect to local broker
        client.connect(mqtt_local_broker, 1883, 60)
        
        # Subscribe to the topic on the local broker
        client.subscribe(mqtt_local_topic)

        # Start listening for messages (non-blocking)
        client.loop_start()

        print("Listening for messages on local broker...")
        while True:
            sleep(1)  # Keeps the program running while listening

    except KeyboardInterrupt:
        print("\nProgram stopped by the user")
    except Exception as e:
        print("Error in subscribe:", e)
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    start_logging()
