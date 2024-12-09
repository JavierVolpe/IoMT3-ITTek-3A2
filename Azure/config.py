class Config:
    MQTT_BROKER_URL = "192.168.87.2"
    MQTT_BROKER_PORT = 1883
    MQTT_KEEPALIVE = 60
    MQTT_TOPIC = "sundhedstjek"
    MQTT_CLIENT_ID = "aeldre1"
    MQTT_USERNAME = ""
    MQTT_PASSWORD = ""

    #SQLALCHEMY_DATABASE_URI = "sqlite:///db.sqlite"
    SQLALCHEMY_DATABASE_URI = (
        "mssql+pyodbc://myadmin:M987yadmin.@miot3.database.windows.net:1433/records"
        "?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30"
    )
    SECRET_KEY = "abc"
    

