from machine import Pin, I2C, ADC, reset
from time import sleep
from umqttsimple import MQTTClient

test_mode = False 

# Pin Definitions
temperature_pin = 4         # DS18B20 an GPIO 4
imu_sda_pin = 21            # SDA an GPIO 21
imu_scl_pin = 22            # SCL an GPIO 22
puls_pin = 34               # Pulssensor an GPIO 34
vibration_motor_pin = 33    # Vibrationsmotor an GPIO 33
buzzer_pin = 27             # Buzzer an GPIO 27
battery_voltage_pin = 32    # Batteriespannung an GPIO 32

# Pin Objects
puls_sensor = Pin(puls_pin, Pin.IN)
vibration_motor = Pin(vibration_motor_pin, Pin.OUT)
buzzer_pin = Pin(buzzer_pin, Pin.OUT)
battery_voltage = Pin(battery_voltage_pin, Pin.IN)
temperature_sensor = Pin(temperature_pin, Pin.IN) 
imu_sda = Pin(imu_sda_pin, Pin.OUT) 
imu_scl = Pin(imu_scl_pin, Pin.OUT) 
imu_i2c = I2C(scl=imu_scl, sda=imu_sda, freq=100000) 
imu_i2c.scan()

# MQTT
mqtt_server = "192.168.87.2"
topic_pub = b"javier/growdata"
topic_sub = b"javier/growcontrol"


# Sleep interval and total sleep time
SLEEP_INTERVAL = 1  # seconds
TOTAL_SLEEP_TIME = 1800  # 30 minutes

def maal_puls():
    return 100

def set_fan_speed(speed):
    return True

def mqtt_callback(topic, msg):
    print("Received message:", msg.decode(), "on topic:", topic.decode())
    # Decode the message and trigger a function
    if msg == b"send_update":
        publish_update()
    elif msg == b"start_fan":
        set_fan_speed(100)
    elif msg == b"stop_fan":
        set_fan_speed(0)
    elif msg == b"reset":
        reset()
    elif msg.decode().startswith("fan_speed_"):
        try:
            speed_percent = int(msg.decode().split("_")[2])
            set_fan_speed(speed_percent)
        except ValueError:
            print("Invalid fan speed value received.")


def publish_update(send=True):
    puls = maal_puls()
    try:   
        msg = f"{puls:.2f}"
        if send:
            client.publish(topic_pub, msg.encode())  # Ensure message is encoded for MQTT
        print(f"Puls: {puls:.2f}")
    except Exception as e:
        print("An error occurred:", e)
        reset()


# MQTT client setup
client = MQTTClient("0001", mqtt_server)

try:
    client.connect() 
    client.set_callback(mqtt_callback)
    client.subscribe(topic_sub)
except OSError as e:
    print("Problem connecting to MQTT broker. Restarting in 10 seconds...")
    print(e)
    sleep(5)
    reset()


if not test_mode:
    while True:
        publish_update()
        # Sleep for the specified interval
        elapsed_sleep_time = 0
        while elapsed_sleep_time < TOTAL_SLEEP_TIME:
            client.check_msg()  # Check for incoming messages
            sleep(SLEEP_INTERVAL)
            elapsed_sleep_time += SLEEP_INTERVAL
else:
    while True:
        publish_update(send=False)
        sleep(2)
        client.check_msg()