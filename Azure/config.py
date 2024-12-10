import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

class Config:
    MQTT_BROKER_URL = "192.168.87.2"
    MQTT_BROKER_PORT = 1883
    MQTT_KEEPALIVE = 60
    MQTT_TOPIC = "sundhedstjek"
    MQTT_CLIENT_ID = "aeldre1"
    MQTT_USERNAME = ""
    MQTT_PASSWORD = ""

    # Fetch credentials from environment variables with default values
    DB_USERNAME = os.getenv('DB_USERNAME', 'SA')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'M987yadmin.')
    DB_HOST = os.getenv('DB_HOST', '20.254.112.3')
    DB_PORT = os.getenv('DB_PORT', 1433)
    DB_NAME = os.getenv('DB_NAME', 'vitale_tegn')

    # AES encryption key (32 bytes for AES-256)
    SECRET_KEY = os.getenv('SECRET_KEY', 'xGkWaUFsH4OB6Iq/2Zb35Pjju7bkKl2/jpX4RXxEdra5tGrTonzMq01maiF5CFhG')  # Get SECRET_KEY from environment

    # Ensure SECRET_KEY is in bytes (not string)
    if isinstance(SECRET_KEY, str):
        SECRET_KEY = SECRET_KEY.encode('utf-8')  # Convert to bytes if it's a string

    # Construct the connection string for pymssql
    SQLALCHEMY_DATABASE_URI = (
        f"mssql+pymssql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    SQLALCHEMY_ECHO = True  # Enable SQLAlchemy echo for debugging (False in production)
