from machine import Pin, I2C, ADC, reset
from time import sleep
from umqttsimple import MQTTClient

test_mode = False 
 
# Pin Definitions
temperature_pin = 4         # DS18B20 an GPIO 4
imu_sda_pin = 21            # SDA an GPIO 21
imu_scl_pin = 22            # SCL an GPIO 22
#puls_pin = 34               # Pulssensor an GPIO 34
vibration_motor_pin = 33    # Vibrationsmotor an GPIO 33
buzzer_pin = 27             # Buzzer an GPIO 27
battery_voltage_pin = 32    # Batteriespannung an GPIO 32

# Pin Objects
#puls_sensor = Pin(puls_pin, Pin.IN)
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

# Puls måler konfig:
# Configuration Constants
ADC_PIN = 34                   # ADC pin where PulseSensor is connected
THRESHOLD = 600                # Threshold for beat detection (adjust as needed)
MIN_BEAT_INTERVAL = 300        # Minimum time (ms) between beats to avoid double counting
INTERVAL_MEMORY = 5            # Number of recent intervals to keep for averaging BPM
NO_BEAT_TIMEOUT = 5000         # If no beat detected within this time (ms), reset BPM to 0
MIN_BPM = 40                   # Minimum realistic BPM
MAX_BPM = 180                  # Maximum realistic BPM
MIN_INTERVALS = 3              # Minimum number of intervals before considering BPM valid

# Setup ADC
puls_maaler = ADC(Pin(ADC_PIN))
puls_maaler.width(ADC.WIDTH_12BIT)     # 12-bit resolution (0-4095)
puls_maaler.atten(ADC.ATTN_11DB)       # Full range: 0-3.6V

# Initialize variables for beat detection
last_beat_time = 0
beat_intervals = []
beat_detected = False
last_detect_time = 0


def measure_bpm(duration_sec=30):
    global last_beat_time, beat_intervals, beat_detected, last_detect_time
    # Reset beat detection variables
    last_beat_time = 0
    beat_intervals = []
    beat_detected = False
    last_detect_time = 0

    print(f"Starting BPM measurement for {duration_sec} seconds...")
    start_time = time.ticks_ms()
    end_time = time.ticks_add(start_time, duration_sec * 1000)
    remaining_time = duration_sec

    while time.ticks_diff(end_time, time.ticks_ms()) > 0:
        sensor_value = puls_maaler.read()
        current_time = time.ticks_ms()

        # Beat Detection
        if sensor_value > THRESHOLD:
            if not beat_detected and (time.ticks_diff(current_time, last_beat_time) > MIN_BEAT_INTERVAL):
                beat_detected = True
                if last_beat_time != 0:
                    interval = time.ticks_diff(current_time, last_beat_time)
                    bpm = 60000 / interval
                    if MIN_BPM <= bpm <= MAX_BPM:
                        beat_intervals.append(interval)
                        if len(beat_intervals) > INTERVAL_MEMORY:
                            beat_intervals.pop(0)
                last_beat_time = current_time
                last_detect_time = current_time
        else:
            beat_detected = False

        # Reset if no beat detected within timeout
        if time.ticks_diff(current_time, last_detect_time) > NO_BEAT_TIMEOUT:
            last_beat_time = 0
            beat_intervals = []
            beat_detected = False
            last_detect_time = current_time

        # Countdown Display
        elapsed_time_sec = time.ticks_diff(current_time, start_time) // 1000
        new_remaining = duration_sec - elapsed_time_sec
        if new_remaining != remaining_time and new_remaining >= 0:
            remaining_time = new_remaining
            print(f"Measurement in progress... {remaining_time} seconds remaining.")

        time.sleep_ms(100)  # Polling interval

    # Calculate Average BPM
    if len(beat_intervals) >= MIN_INTERVALS:
        avg_interval = sum(beat_intervals) / len(beat_intervals)
        avg_bpm = 60000 / avg_interval
        if MIN_BPM <= avg_bpm <= MAX_BPM:
            avg_bpm = round(avg_bpm, 1)
        else:
            avg_bpm = 0
    else:
        avg_bpm = 0

    if avg_bpm > 0:
        print(f"Measurement complete. Average BPM over {duration_sec} seconds: {avg_bpm}")
    else:
        print("Could not determine BPM. Please try again.")
    return avg_bpm


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
    puls = measure_bpm()
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