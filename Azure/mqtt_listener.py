import paho.mqtt.client as mqtt
from config import Config
import logging
import smtplib
from email.mime.text import MIMEText

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MQTTListener")

# Email Configuration (Update these with your actual email server and credentials)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your_email@gmail.com"   # Replace with your email
SMTP_PASSWORD = "your_email_password"    # Replace with your email's app password or credentials
EMAIL_FROM = "your_email@gmail.com"
EMAIL_TO = "recipient@example.com"       # Replace with the recipient's email address
EMAIL_SUBJECT = "Critical MQTT Alert"

def send_email_alert(message):
    """
    Sends an email alert using SMTP with the given message.
    """
    msg = MIMEText(f"A critical alert message was received:\n\n{message}")
    msg["Subject"] = EMAIL_SUBJECT
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Start TLS for security
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Email alert sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
        client.subscribe("critical")  # Subscribe to the 'critical' topic
        logger.info("Subscribed to 'critical' topic.")
    else:
        logger.error(f"Failed to connect to MQTT broker, return code {rc}")

def on_message(client, userdata, msg):
    message = msg.payload.decode('utf-8', errors='replace')
    logger.info(f"Received message on topic '{msg.topic}': {message}")

    # If we receive a message on the 'critical' topic, send an email alert.
    # You can add conditions here if you only want to send emails when certain criteria are met.
    if msg.topic == "critical":
        send_email_alert(message)

def start_mqtt_listener():
    client = mqtt.Client()
    if Config.MQTT_USERNAME and Config.MQTT_PASSWORD:
        client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(Config.MQTT_BROKER_URL, Config.MQTT_BROKER_PORT, keepalive=Config.MQTT_KEEPALIVE)
        logger.info("Starting MQTT loop...")
        client.loop_forever()
    except Exception as e:
        logger.error(f"Error connecting to MQTT broker: {e}")

if __name__ == "__main__":
    # Run the MQTT listener in this file directly.
    start_mqtt_listener()
