from time import sleep
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

mqtt_remote_broker  = "20.0.194.60"  
mqtt_remote_user    = "Plejehjem1"
mqtt_remote_pass    = "P987lejehjem1."
mqtt_local_broker   = "192.168.1.106"
mqtt_local_user     = "user2"
mqtt_local_pass     = "U987ser2."

# This function is triggered when a message is received from any broker
def send_data(client, userdata, message):
    msg_str = message.payload.decode("utf-8")

    print(f"Received message from {message.topic} broker: {msg_str}")

    try:
        # Forward the message to the opposite broker
        if message.topic.startswith("sundhed"):
            if message.topic.startswith("sundhed/"):
                # Forward from local to remote
                publish.single(message.topic, str(msg_str), hostname=mqtt_remote_broker, auth={'username': mqtt_remote_user, 'password': mqtt_remote_pass})
                print(f"Data forwarded to remote broker at {mqtt_remote_broker} with topic {message.topic}")
            else:
                # Forward from remote to local
                publish.single(message.topic, str(msg_str), hostname=mqtt_local_broker, auth={'username': mqtt_local_user, 'password': mqtt_local_pass})
                print(f"Data forwarded to local broker at {mqtt_local_broker} with topic {message.topic}")

    except Exception as e:
        print("Error:", e)
        print("Failed to forward message")

    sleep(0.5)

def start_logging():
    """
    This function starts the logging process.
    """
    try:
        # Create MQTT client for both brokers
        client = mqtt.Client()
        client.username_pw_set(mqtt_local_user, mqtt_local_pass)
        client.on_message = send_data

        # Connect to local broker
        client.connect(mqtt_local_broker, 1883, 60)
        
        # Subscribe to all topics on the local broker
        client.subscribe("#", qos=1)

        # Connect to remote broker
        client.connect(mqtt_remote_broker, 1883, 60)
        
        # Subscribe to all topics on the remote broker
        client.subscribe("#", qos=1)

        # Start listening for messages from both brokers (non-blocking)
        client.loop_start()

        print("Listening for messages on both brokers...")
        while True:
            sleep(1)  # Keeps the program running while listening

    except Exception as e:
        print("Error in subscribe:", e)
    except KeyboardInterrupt:
        print("Program stopped by the user")

start_logging()
