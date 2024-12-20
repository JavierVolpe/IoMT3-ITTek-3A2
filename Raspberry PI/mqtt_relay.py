import logging
from time import sleep
import paho.mqtt.client as mqtt
from paho.mqtt.publish import single
import threading
import time
from threading import Lock

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MQTT Configuration
# Remote Broker
MQTT_REMOTE_BROKER = "10.129.58.1"  
MQTT_REMOTE_PORT = 1883
MQTT_REMOTE_TOPIC = "sundhed/#"  # Subscribe to all subtopics under sundhed
MQTT_REMOTE_USER = "Plejehjem1"
MQTT_REMOTE_PASS = "P987lejehjem1."

# Local Broker
MQTT_LOCAL_BROKER = "localhost"
MQTT_LOCAL_PORT = 1883
MQTT_LOCAL_TOPIC = "sundhed/#"  # Subscribe to all subtopics under sundhed
MQTT_LOCAL_USER = "user2"
MQTT_LOCAL_PASS = "U987ser2."

# Cache to store recently forwarded messages to prevent loops
FORWARDED_CACHE = {}
CACHE_TTL = 10  # seconds
cache_lock = Lock()

def normalize_payload(payload):
    return payload.strip()

def cache_cleanup():
    """
    Periodically cleans up expired entries in the FORWARDED_CACHE.
    """
    while True:
        current_time = time.time()
        with cache_lock:
            expired_keys = [k for k, v in FORWARDED_CACHE.items() if current_time - v > CACHE_TTL]
            for k in expired_keys:
                del FORWARDED_CACHE[k]
                logger.debug(f"Cache entry expired and removed: {k}")
        sleep(10)

def forward_message(source, target_broker, target_port, target_user, target_pass, topic, payload):
    """
    Forwards a message to the target broker on the same topic.
    """
    key = (source, topic, payload)
    with cache_lock:
        if key in FORWARDED_CACHE:
            logger.debug(f"Message already forwarded: {key}. Skipping.")
            return
        try:
            single(
                topic=topic,
                payload=payload,
                hostname=target_broker,
                port=target_port,
                auth={'username': target_user, 'password': target_pass},
                qos=1
            )
            logger.info(f"Forwarded message from {source} to {target_broker} on topic '{topic}'")
            # Add to cache to prevent loop
            FORWARDED_CACHE[key] = time.time()
        except Exception as e:
            logger.error(f"Failed to forward message from {source} to {target_broker}: {e}")

def on_message_local(client, userdata, message):
    """
    Callback for messages received from the local broker.
    Forwards messages to the remote broker.
    """
    payload = normalize_payload(message.payload.decode("utf-8"))
    topic = message.topic

    # Check if message was forwarded from remote to local
    key = ('REMOTE', topic, payload)
    with cache_lock:
        if key in FORWARDED_CACHE:
            logger.debug(f"Received a message that was forwarded from REMOTE: {payload}. Ignoring.")
            return

    logger.info(f"Received message from LOCAL broker on topic '{topic}': {payload}")
    forward_message(
        source="LOCAL",
        target_broker=MQTT_REMOTE_BROKER,
        target_port=MQTT_REMOTE_PORT,
        target_user=MQTT_REMOTE_USER,
        target_pass=MQTT_REMOTE_PASS,
        topic=topic,
        payload=payload
    )

def on_message_remote(client, userdata, message):
    """
    Callback for messages received from the remote broker.
    Forwards messages to the local broker.
    """
    payload = normalize_payload(message.payload.decode("utf-8"))
    topic = message.topic

    # Check if message was forwarded from local to remote
    key = ('LOCAL', topic, payload)
    with cache_lock:
        if key in FORWARDED_CACHE:
            logger.debug(f"Received a message that was forwarded from LOCAL: {payload}. Ignoring.")
            return

    logger.info(f"Received message from REMOTE broker on topic '{topic}': {payload}")
    forward_message(
        source="REMOTE",
        target_broker=MQTT_LOCAL_BROKER,
        target_port=MQTT_LOCAL_PORT,
        target_user=MQTT_LOCAL_USER,
        target_pass=MQTT_LOCAL_PASS,
        topic=topic,
        payload=payload
    )

def on_connect_local(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to LOCAL MQTT broker successfully.")
        client.subscribe(MQTT_LOCAL_TOPIC, qos=1)
        logger.info(f"Subscribed to LOCAL topic '{MQTT_LOCAL_TOPIC}'")
    else:
        logger.error(f"Failed to connect to LOCAL MQTT broker. Return code: {rc}")

def on_connect_remote(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to REMOTE MQTT broker successfully.")
        client.subscribe(MQTT_REMOTE_TOPIC, qos=1)
        logger.info(f"Subscribed to REMOTE topic '{MQTT_REMOTE_TOPIC}'")
    else:
        logger.error(f"Failed to connect to REMOTE MQTT broker. Return code: {rc}")

def setup_client(broker, port, user, password, on_connect, on_message, client_id):
    """
    Sets up and returns an MQTT client.
    """
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    client.username_pw_set(username=user, password=password)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(broker, port, keepalive=60)
    client.loop_start()
    return client

def start_relay():
    """
    Initializes both MQTT clients (local and remote) and starts the relay process.
    """
    # Start cache cleanup thread
    cleanup_thread = threading.Thread(target=cache_cleanup, daemon=True)
    cleanup_thread.start()
    logger.debug("Started cache cleanup thread.")

    # Setup LOCAL client
    local_client = setup_client(
        broker=MQTT_LOCAL_BROKER,
        port=MQTT_LOCAL_PORT,
        user=MQTT_LOCAL_USER,
        password=MQTT_LOCAL_PASS,
        on_connect=on_connect_local,
        on_message=on_message_local,
        client_id="relay_local_to_remote"
    )

    # Setup REMOTE client
    remote_client = setup_client(
        broker=MQTT_REMOTE_BROKER,
        port=MQTT_REMOTE_PORT,
        user=MQTT_REMOTE_USER,
        password=MQTT_REMOTE_PASS,
        on_connect=on_connect_remote,
        on_message=on_message_remote,
        client_id="relay_remote_to_local"
    )

    logger.info("Bidirectional MQTT relay is running...")
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        logger.info("Relay stopped by user.")
    finally:
        local_client.loop_stop()
        local_client.disconnect()
        remote_client.loop_stop()
        remote_client.disconnect()
        logger.info("MQTT clients disconnected and relay has been shut down.")

if __name__ == "__main__":
    start_relay()
