from time import sleep
import paho.mqtt.client as mqtt

mqtt_local_broker  = "20.0.194.60"  
mqtt_local_topic   = "sundhed/data" 
mqtt_local_user    = "Plejehjem1"
mqtt_local_pass    = "P987lejehjem1."

# This function is triggered when a message is received from the local broker
def send_data(client, userdata, message):
    msg_str = message.payload.decode("utf-8")

    print(f"Received message: {msg_str}")
    
    if msg_str.startswith("help_"):
        print("Help message received, sending mail")

    sleep(0.5)

def start_logging():
    """
    This function starts the logging process.
    """
    try:
        # Create MQTT client for local broker
        client = mqtt.Client()
        client.username_pw_set(mqtt_local_user, mqtt_local_pass)
        client.on_message = send_data

        # Connect to local broker
        client.connect(mqtt_local_broker, 1883, 60)
        
        # Subscribe to the topic on the local broker
        client.subscribe(mqtt_local_topic, qos=1)

        # Start listening for messages (non-blocking)
        client.loop_start()

        print("Listening for messages on local broker...")
        while True:
            sleep(1)  # Keeps the program running while listening

    except Exception as e:
        print("Error in subscribe:", e)
    except KeyboardInterrupt:
        print("Program stopped by the user")

start_logging()
 