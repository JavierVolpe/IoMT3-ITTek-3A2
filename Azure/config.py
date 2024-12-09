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
        "mssql+pyodbc://SA:M987yadmin.@20.254.112.3:1433/vitale_tegn"
        "?driver=ODBC+Driver+18+for+SQL+Server"
        "&Encrypt=yes&TrustServerCertificate=yes"
    )
    SECRET_KEY = "abc"
    

