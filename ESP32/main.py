from machine import Pin, I2C, ADC, reset, PWM
from time import ticks_ms, ticks_add, ticks_diff, sleep
from umqttsimple import MQTTClient

test_mode = False

# Pin Definitions
temperature_pin = 4
imu_sda_pin = 21
imu_scl_pin = 22
vibration_motor_pin = 33
buzzer_pin = 27
battery_voltage_pin = 32

# Pin Objects
vibration_motor = Pin(vibration_motor_pin, Pin.OUT)
buzzer_pin = Pin(buzzer_pin, Pin.OUT)
battery_voltage = Pin(battery_voltage_pin, Pin.IN)
temperature_sensor = Pin(temperature_pin, Pin.IN)
imu_sda = Pin(imu_sda_pin, Pin.OUT)
imu_scl = Pin(imu_scl_pin, Pin.OUT)
imu_i2c = I2C(scl=imu_scl, sda=imu_sda, freq=100000)
imu_i2c.scan()

# MQTT Settings (Hardcoded credentials)
mqtt_server = "192.168.137.49"
mqtt_user = "user1"  # Hardcoded username
mqtt_pass = "R987pi."  # Hardcoded password
topic_pub = b"sundhed/data"
topic_sub = b"sundhed/growcontrol"

# Sleep Interval and Total Sleep Time
SLEEP_INTERVAL = 1000  # milliseconds (1 second)
TOTAL_SLEEP_TIME = 1800 * 1000  # 30 minutes in milliseconds

# Puls Måler Config
ADC_PIN = 34
THRESHOLD = 600
MIN_BEAT_INTERVAL = 300
INTERVAL_MEMORY = 5
NO_BEAT_TIMEOUT = 5000
MIN_BPM = 40
MAX_BPM = 180
MIN_INTERVALS = 3

# Setup ADC
puls_maaler = ADC(Pin(ADC_PIN))
puls_maaler.width(ADC.WIDTH_12BIT)
puls_maaler.atten(ADC.ATTN_11DB)

# Initialize variables for beat detection
last_beat_time = 0
beat_intervals = []
beat_detected = False
last_detect_time = 0


def measure_bpm(duration_sec=30):
    global last_beat_time, beat_intervals, beat_detected, last_detect_time
    last_beat_time = 0
    beat_intervals.clear()
    beat_detected = False
    last_detect_time = 0

    start_time = ticks_ms()
    end_time = ticks_add(start_time, duration_sec * 1000)
    remaining_time = duration_sec

    while ticks_diff(end_time, ticks_ms()) > 0:
        sensor_value = puls_maaler.read()
        current_time = ticks_ms()

        # Beat Detection
        if sensor_value > THRESHOLD:
            if not beat_detected and ticks_diff(current_time, last_beat_time) > MIN_BEAT_INTERVAL:
                beat_detected = True
                if last_beat_time != 0:
                    interval = ticks_diff(current_time, last_beat_time)
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
        if ticks_diff(current_time, last_detect_time) > NO_BEAT_TIMEOUT:
            last_beat_time = 0
            beat_intervals.clear()
            beat_detected = False
            last_detect_time = current_time

        # Countdown Display
        elapsed_time_sec = ticks_diff(current_time, start_time) // 1000
        new_remaining = duration_sec - elapsed_time_sec
        if new_remaining != remaining_time and new_remaining >= 0:
            remaining_time = new_remaining
            print(f"Measurement in progress... {remaining_time} seconds remaining.")

        # Non-blocking waiting
        while ticks_diff(ticks_ms(), current_time) < 100:
            client.check_msg()  # Ensure MQTT messages are checked during wait

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
    return round(avg_bpm)


def mqtt_callback(topic, msg):
    print("Received message:", msg.decode(), "on topic:", topic.decode())
    if msg == b"send_update":
        print("Requested update. Sending.")
        publish_update()
    elif msg == b"reset":
        reset()


def publish_update(send=True):
    puls = measure_bpm()
    try:
        msg = f"{puls:.2f}"
        if send:
            client.publish(topic_pub, msg.encode())
        print(f"Puls: {puls:.2f}")
    except Exception as e:
        print("An error occurred:", e)
        reset()


# MQTT client setup (Using hardcoded credentials)
def connect_mqtt():
    client = MQTTClient("0001", mqtt_server, user=mqtt_user, password=mqtt_pass)
    client.set_callback(mqtt_callback)
    
    # Ensure that we connect successfully and retry if not
    while True:
        try:
            client.connect()
            print("Connected to MQTT broker")
            break
        except Exception as e:
            print("Error connecting to MQTT broker:", e)
            sleep(5)  # Wait before retrying
            
    client.subscribe(topic_sub)
    return client


client = connect_mqtt()


def main_loop():
    start_time = ticks_ms()
    while True:
        current_time = ticks_ms()
        elapsed_time = ticks_diff(current_time, start_time)
        
        if elapsed_time < TOTAL_SLEEP_TIME:
            client.check_msg()  # Check for incoming MQTT messages
        else:
            print("Total sleep time reached.")
            break
        
        # Non-blocking wait to check messages every SLEEP_INTERVAL
        while ticks_diff(ticks_ms(), current_time) < SLEEP_INTERVAL:
            pass


if __name__ == "__main__":
    main_loop()

