import uasyncio as asyncio
from machine import Pin, I2C, ADC, reset, PWM
from umqttsimple import MQTTClient

# ---------------------------
# Hardware Configuration
# ---------------------------

# MPU6050 Settings
MPU6050_ADDR = 0x68
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
ACCEL_SENSITIVITY = 16384.0  # ±2g range

# Pin Definitions
# Ensure no pin conflicts between functionalities
vibration_motor_pin = 16      # From fall detection
reset_button_pin = 17          # From fall detection
temperature_pin = 4            # From pulse measurement
buzzer_pin = 27                # Optional, not used in current logic
battery_voltage_pin = 32        # Optional, not used in current logic
ADC_PIN = 34                   # Pulse sensor

# Initialize PWM for Vibration Motor
vibration_motor = PWM(Pin(vibration_motor_pin))
vibration_motor.freq(1000)  # Set frequency to 1 kHz
vibration_motor.duty(0)      # Start with motor off

# Initialize Reset Button
reset_button = Pin(reset_button_pin, Pin.IN, Pin.PULL_UP)

# Initialize ADC for Pulse Sensor
puls_maaler = ADC(Pin(ADC_PIN))
puls_maaler.width(ADC.WIDTH_12BIT)
puls_maaler.atten(ADC.ATTN_11DB)

# Initialize I2C for MPU6050
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)

# Initialize Other Pins (if needed)
temperature_sensor = Pin(temperature_pin, Pin.IN)
battery_voltage = Pin(battery_voltage_pin, Pin.IN)
buzzer = Pin(buzzer_pin, Pin.OUT)  # Not currently used

# ---------------------------
# MQTT Settings (Hardcoded)
# ---------------------------
mqtt_server = "192.168.137.49"
mqtt_user = "user1"
mqtt_pass = "R987pi."
topic_pub = b"sundhed/data"
topic_sub = b"sundhed/growcontrol"

# ---------------------------
# Pulse Sensor Configuration
# ---------------------------
THRESHOLD = 600
MIN_BEAT_INTERVAL = 300
INTERVAL_MEMORY = 5
NO_BEAT_TIMEOUT = 5000
MIN_BPM = 40
MAX_BPM = 180
MIN_INTERVALS = 3

# Initialize beat detection variables
last_beat_time = 0
beat_intervals = []
beat_detected = False
last_detect_time = 0

# ---------------------------
# MPU6050 Functions
# ---------------------------
def write_mpu6050(reg, value):
    i2c.writeto_mem(MPU6050_ADDR, reg, bytes([value]))

def read_raw_data(reg):
    try:
        data = i2c.readfrom_mem(MPU6050_ADDR, reg, 2)
        high = data[0]
        low = data[1]
        value = (high << 8) | low
        if value > 32767:
            value -= 65536
        return value
    except OSError as e:
        print(f"Error reading MPU6050 data: {e}")
        return 0

def mpu6050_init():
    try:
        write_mpu6050(PWR_MGMT_1, 0)  # Wake up MPU6050
        print("MPU6050 Initialized")
    except Exception as e:
        print(f"Failed to initialize MPU6050: {e}")
        reset()

def read_accelerometer():
    accel_x_raw = read_raw_data(ACCEL_XOUT_H)
    accel_y_raw = read_raw_data(ACCEL_XOUT_H + 2)
    accel_z_raw = read_raw_data(ACCEL_XOUT_H + 4)
    accel_x = accel_x_raw / ACCEL_SENSITIVITY
    accel_y = accel_y_raw / ACCEL_SENSITIVITY
    accel_z = accel_z_raw / ACCEL_SENSITIVITY
    return accel_x, accel_y, accel_z

# ---------------------------
# Motor Control
# ---------------------------
def set_vibration(intensity):
    if 0 <= intensity <= 1023:
        vibration_motor.duty(intensity)
        print(f"Vibration motor set to intensity: {intensity}")
    else:
        print("Error: Intensity must be between 0 and 1023")

# ---------------------------
# Pulse Measurement Function
# ---------------------------
async def measure_bpm():
    global last_beat_time, beat_intervals, beat_detected, last_detect_time
    last_beat_time = 0
    beat_intervals = []
    beat_detected = False
    last_detect_time = 0

    duration_sec = 30
    start_time = ticks_ms()
    end_time = ticks_add(start_time, duration_sec * 1000)
    remaining_time = duration_sec

    print(f"Starting BPM measurement for {duration_sec} seconds...")

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
                        print(f"Beat detected. Current BPM: {bpm:.2f}")
                last_beat_time = current_time
                last_detect_time = current_time
        else:
            beat_detected = False

        # Reset if no beat detected within timeout
        if ticks_diff(current_time, last_detect_time) > NO_BEAT_TIMEOUT:
            last_beat_time = 0
            beat_intervals = []
            beat_detected = False
            last_detect_time = current_time

        # Countdown Display
        elapsed_time_sec = ticks_diff(current_time, start_time) // 1000
        new_remaining = duration_sec - elapsed_time_sec
        if new_remaining != remaining_time and new_remaining >= 0:
            remaining_time = new_remaining
            print(f"Measurement in progress... {remaining_time} seconds remaining.")

        # Allow other tasks to run
        await asyncio.sleep_ms(100)

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
        print(f"Measurement complete. Average BPM: {avg_bpm}")
    else:
        print("Could not determine BPM. Please try again.")
    return avg_bpm

# ---------------------------
# MQTT Functions
# ---------------------------
def mqtt_callback(topic, msg):
    print("Received message:", msg.decode(), "on topic:", topic.decode())
    if msg == b"send_update":
        print("Requested update. Sending.")
        asyncio.create_task(publish_update())
    elif msg == b"reset":
        print("Reset command received.")
        asyncio.create_task(reset_alarm())

async def publish_update():
    bpm = await measure_bpm()
    try:
        msg = f"{bpm:.2f}"
        client.publish(topic_pub, msg.encode())
        print(f"Puls: {bpm:.2f}")
    except Exception as e:
        print("An error occurred while publishing:", e)
        reset()

async def reset_alarm():
    global alarm_active
    print("Resetting alarm...")
    alarm_active = False
    set_vibration(0)  # Turn off motor

async def connect_mqtt():
    client = MQTTClient("0001", mqtt_server, user=mqtt_user, password=mqtt_pass)
    client.set_callback(mqtt_callback)

    while True:
        try:
            client.connect()
            print("Connected to MQTT broker")
            break
        except Exception as e:
            print("Error connecting to MQTT broker:", e)
            await asyncio.sleep(5)

    client.subscribe(topic_sub)
    return client

# ---------------------------
# Fall Detection Task
# ---------------------------
async def fall_detection_task():
    global alarm_active
    alarm_active = False
    while True:
        accel_x, accel_y, accel_z = read_accelerometer()
        # Uncomment below to see accelerometer values for debugging
        # print(f"Accelerometer (g): X={accel_x:.3f}, Y={accel_y:.3f}, Z={accel_z:.3f}")

        # Check for fall detection
        if not alarm_active and (accel_x > 1.2 or accel_y > 1.2 or accel_z > 1.2):
            print("Fall detected!")
            alarm_active = True
            set_vibration(1023)  # Turn on motor at full intensity

        # Check if alarm is active and reset via button
        if alarm_active and reset_button.value() == 0:
            print("Reset button pressed! Stopping alarm...")
            await reset_alarm()

        # Allow other tasks to run
        await asyncio.sleep_ms(100)

# ---------------------------
# Main Function
# ---------------------------
async def main():
    # Initialize MPU6050
    mpu6050_init()

    # Connect to MQTT
    global client
    client = await connect_mqtt()

    # Start fall detection task
    asyncio.create_task(fall_detection_task())

    # Keep the main coroutine alive to allow other tasks to run
    while True:
        await asyncio.sleep(1)  # Adjust as needed

# Run the main function
try:
    asyncio.run(main())
except Exception as e:
    print("Unhandled exception:", e)
    reset()

