import uasyncio as asyncio
from machine import Pin, I2C, ADC, PWM, reset
from umqttsimple import MQTTClient
from time import ticks_ms, ticks_diff, ticks_add

# Hardware Configuration
vibration_motor = PWM(Pin(16))
vibration_motor.freq(1000)
reset_button = Pin(17, Pin.IN, Pin.PULL_UP)
emergency_button = Pin(18, Pin.IN, Pin.PULL_UP)
pulse_sensor = ADC(Pin(34))
pulse_sensor.width(ADC.WIDTH_12BIT)
pulse_sensor.atten(ADC.ATTN_11DB)
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)

# MQTT Configuration
MQTT_SERVER = "192.168.1.106"
MQTT_USER = "user2"
MQTT_PASS = "U987ser2."
TOPIC_PUB = b"sundhed/data"
TOPIC_SUB = b"sundhed/control"
mqtt_client = MQTTClient("client0001", MQTT_SERVER, user=MQTT_USER, password=MQTT_PASS)

# BPM Measurement Constants
MIN_BPM = 40
MAX_BPM = 180
INTERVAL_MEMORY = 10
MIN_INTERVALS = 5
NO_BEAT_TIMEOUT = 3000  # Increased timeout
THRESHOLD = 500  # Adjust based on sensor calibration

# Globals
MPU6050_ADDR = 0x68
ACCEL_THRESHOLD = 2.5
MIN_BEAT_INTERVAL = 500
alarm_active = False

# MPU6050 Functions
def write_mpu6050(reg, value):
    i2c.writeto_mem(MPU6050_ADDR, reg, bytes([value]))

def read_accel_magnitude():
    try:
        accel_x_raw = i2c.readfrom_mem(MPU6050_ADDR, 0x3B, 2)
        accel_y_raw = i2c.readfrom_mem(MPU6050_ADDR, 0x3D, 2)
        accel_z_raw = i2c.readfrom_mem(MPU6050_ADDR, 0x3F, 2)

        def to_signed(val):
            return val - 65536 if val > 32767 else val

        accel_x = to_signed(accel_x_raw[0] << 8 | accel_x_raw[1]) / 16384.0
        accel_y = to_signed(accel_y_raw[0] << 8 | accel_y_raw[1]) / 16384.0
        accel_z = to_signed(accel_z_raw[0] << 8 | accel_z_raw[1]) / 16384.0

        return (accel_x ** 2 + accel_y ** 2 + accel_z ** 2) ** 0.5
    except OSError as e:
        print(f"Error reading accelerometer: {e}")
        return 0

# Vibration Control
def set_vibration(intensity):
    vibration_motor.duty(intensity)

# MQTT Callback
def mqtt_callback(topic, msg):
    try:
        message = msg.decode()
        print("Received message:", message, "on topic:", topic.decode())
        if message == "send_update":
            print("Requested update. Sending.")
            asyncio.create_task(publish_update())
        elif message == "reset":
            print("Reset command received.")
            asyncio.create_task(reset_alarm())
        else:
            print(f"Unknown command: {message}")
    except Exception as e:
        print(f"Error in MQTT callback: {e}")

# BPM Measurement Function
async def measure_bpm(duration_sec=30):
    print(f"Starting BPM measurement for {duration_sec} seconds...")
    
    # Reset beat detection variables
    last_beat_time = 0
    beat_intervals = []
    beat_detected = False
    last_detect_time = 0
    
    start_time = ticks_ms()
    end_time = ticks_add(start_time, duration_sec * 1000)
    remaining_time = duration_sec

    while ticks_diff(end_time, ticks_ms()) > 0:
        sensor_value = pulse_sensor.read()
        # Uncomment the next line for debugging raw sensor values
        # print(f"Raw sensor value: {sensor_value}")
        current_time = ticks_ms()

        # Beat Detection
        if sensor_value > THRESHOLD:
            if not beat_detected and (last_beat_time == 0 or ticks_diff(current_time, last_beat_time) > MIN_BEAT_INTERVAL):
                beat_detected = True
                if last_beat_time != 0:
                    interval = ticks_diff(current_time, last_beat_time)
                    bpm = 60000 / interval
                    if MIN_BPM <= bpm <= MAX_BPM:
                        beat_intervals.append(interval)
                        if len(beat_intervals) > INTERVAL_MEMORY:
                            beat_intervals.pop(0)
                        print(f"Detected beat. Interval: {interval} ms, BPM: {bpm:.1f}")
                last_beat_time = current_time
                last_detect_time = current_time
        else:
            beat_detected = False

        # Reset beat detection variables if no beat detected within timeout
        if ticks_diff(current_time, last_detect_time) > NO_BEAT_TIMEOUT:
            last_beat_time = 0
            beat_detected = False
            last_detect_time = current_time
            print("No beat detected for timeout duration. Resetting beat detection.")
            # Do not reset beat_intervals here

        # Countdown Display
        elapsed_time_sec = ticks_diff(current_time, start_time) // 1000
        new_remaining = duration_sec - elapsed_time_sec
        if new_remaining != remaining_time and new_remaining >= 0:
            remaining_time = new_remaining
            print(f"Measurement in progress... {remaining_time} seconds remaining.")
        
        await asyncio.sleep_ms(100)  # Polling interval

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

# Tasks
async def fall_detection_task():
    global alarm_active
    while True:
        magnitude = read_accel_magnitude()
        # print(f"Accel Magnitude: {magnitude:.2f}")  # Optional debug
        if magnitude > ACCEL_THRESHOLD and not alarm_active:
            alarm_active = True
            print("Fall detected!")
            set_vibration(1023)
        if alarm_active and reset_button.value() == 0:
            await reset_alarm()
        await asyncio.sleep_ms(100)

async def reset_alarm():
    global alarm_active
    alarm_active = False
    set_vibration(0)
    print("Alarm reset.")

async def emergency_button_task():
    while True:
        if emergency_button.value() == 0:
            print("Emergency button pressed! Sending alert.")
            mqtt_client.publish(TOPIC_PUB, f"{MQTT_ID:Emergency")
        await asyncio.sleep_ms(100)

async def publish_update():
    bpm = await measure_bpm()
    if bpm > 0:
        mqtt_client.publish(TOPIC_PUB, f"BPM: {bpm}".encode())
    else:
        mqtt_client.publish(TOPIC_PUB, "BPM: N/A".encode())
    print("BPM data published via MQTT.")

async def connect_mqtt():
    mqtt_client.set_callback(mqtt_callback)
    mqtt_client.connect()
    mqtt_client.subscribe(TOPIC_SUB)
    print(f"Connected to MQTT broker. Subscribed to {TOPIC_SUB.decode()}")

# Main
async def main():
    write_mpu6050(0x6B, 0)  # Wake MPU6050
    try:
        await connect_mqtt()
    except Exception as e:
        print(f"Error MQTT : {e}")
    
    asyncio.create_task(fall_detection_task())
    asyncio.create_task(emergency_button_task())
    
    while True:
        try:
            mqtt_client.check_msg()  # Process incoming MQTT messages
        except Exception as e:
            print(f"Error checking MQTT messages: {e}")
            # Optionally, attempt to reconnect or handle the error
        await asyncio.sleep(0.1)  # Small sleep to prevent tight looping

# Run the main coroutine
try:
    asyncio.run(main())
except Exception as e:
    print(f"Error: {e}")
    # Optionally, reset or handle the error

