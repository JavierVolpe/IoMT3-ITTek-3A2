class Config:
    MQTT_BROKER_URL = "192.168.87.2"
    MQTT_BROKER_PORT = 1883
    MQTT_KEEPALIVE = 60
    MQTT_TOPIC = "sundhedstjek"
    MQTT_CLIENT_ID = "aeldre1"
    MQTT_USERNAME = ""
    MQTT_PASSWORD = ""

    SQLALCHEMY_DATABASE_URI = "sqlite:///db.sqlite"
    SECRET_KEY = "abc"
    

