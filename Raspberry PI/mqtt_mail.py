from time import sleep
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

mqtt_remote_broker  = "20.0.194.60"  
mqtt_remote_topic   = "sundhed/data" 
mqtt_remote_user    = "Plejehjem1"
mqtt_remote_pass    = "P987lejehjem1."
mqtt_local_broker   = "192.168.137.49"
mqtt_local_user     = "user1"
mqtt_local_pass     = "U987ser1."
mqtt_local_topic    = "sundhed/data"

# This function is triggered when a message is received from the local broker
def send_data(client, userdata, message):
    msg_str = message.payload.decode("utf-8")

    print(f"Received message from local broker: {msg_str}")
    
    if msg_str.startswith("help_"):
        print("Help message received, sending to remote broker AND MAIL")


    try:
        # Send the received data to the remote broker
        publish.single(mqtt_remote_topic, str(msg_str), hostname=mqtt_remote_broker, auth={'username': mqtt_remote_user, 'password': mqtt_remote_pass})
        print(f"Data sent to the remote broker at {mqtt_remote_broker} with topic {mqtt_remote_topic}")
    except Exception as e:
        print("Error:", e)
        print("Failed to connect to the remote broker")

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
 