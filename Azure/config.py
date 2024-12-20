import os


class Config:
    MQTT_BROKER_URL = "localhost"
    MQTT_BROKER_PORT = 1883
    MQTT_KEEPALIVE = 60
    MQTT_TOPIC = "sundhed/data"
    MQTT_CONTROL_TOPIC = "sundhed/control"
    MQTT_CLIENT_ID = "Plejehjem1"
    MQTT_USERNAME = "Plejehjem1"
    MQTT_PASSWORD = "P987lejehjem1."

    # Fetch credentials from environment variables with default values
    DB_USERNAME = "SA"
    DB_PASSWORD = "M987yadmin."
    DB_HOST = "20.254.112.3"
    DB_PORT = "1433"
    DB_NAME = "vitale_tegn"

    # AES encryption key (32 bytes for AES-256)
    SECRET_KEY = "ijn9RML8M9EeNx3Y"

    # Ensure SECRET_KEY is in bytes (not string)
    if isinstance(SECRET_KEY, str):
        SECRET_KEY = SECRET_KEY.encode('utf-8')  # Convert to bytes if it's a string

    # Construct the connection string for pymssql
    SQLALCHEMY_DATABASE_URI = (
        f"mssql+pymssql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    SQLALCHEMY_ECHO = False  
