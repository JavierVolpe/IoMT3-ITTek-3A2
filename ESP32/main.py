import uasyncio as asyncio
from machine import Pin, I2C, ADC, PWM, reset
from umqttsimple import MQTTClient
from time import ticks_ms, ticks_diff, ticks_add

# Pin Definitions
ADC_PIN = 32
VIBRATION_MOTOR_PIN = 27
RESET_BUTTON_PIN = 2
EMERGENCY_BUTTON_PIN = 15
PULSE_SENSOR_PIN = 34
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21

# MQTT Configuration
MQTT_SERVER = "192.168.137.91"
MQTT_USER = "user2"
MQTT_PASS = "U987ser2."
TOPIC_PUB = b"sundhed/data"
TOPIC_SUB = b"sundhed/control"
MQTT_ID = "010101-1111"

# BPM Measurement Constants
MIN_BPM = 40
MAX_BPM = 180
INTERVAL_MEMORY = 10
MIN_INTERVALS = 5
NO_BEAT_TIMEOUT = 3000  # Increased timeout in milliseconds
THRESHOLD = 500  # Adjust based on sensor calibration

# Debounce Constants for Emergency Button
DEBOUNCE_INTERVAL_MS = 200  # 200 milliseconds debounce interval

# Globals
MPU6050_ADDR = 0x68
ACCEL_THRESHOLD = 2.5
MIN_BEAT_INTERVAL = 500
alarm_active = False
bpm_measurement_running = False  # Flag to prevent overlapping measurements
fall_alarm_timer = None  # Reference to the fall alarm timer task

# Battery Voltage Calculation
R1 = 6200.0   # 6.2kΩ
R2 = 5600.0   # 5.6kΩ
ADC_MAX = 4095.0
ADC_VREF = 3.6  
BATTERY_MIN_VOLT = 3.7
BATTERY_MAX_VOLT = 4.2
scale_factor = 0.781
offset = 0.388

# Hardware Configuration
vibration_motor = PWM(Pin(VIBRATION_MOTOR_PIN))
vibration_motor.freq(1000)

reset_button = Pin(RESET_BUTTON_PIN, Pin.IN, Pin.PULL_UP)
emergency_button = Pin(EMERGENCY_BUTTON_PIN, Pin.IN, Pin.PULL_UP)

pulse_sensor = ADC(Pin(PULSE_SENSOR_PIN))
pulse_sensor.width(ADC.WIDTH_12BIT)
pulse_sensor.atten(ADC.ATTN_11DB)

i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=400000)

bat_adc = ADC(Pin(ADC_PIN))
bat_adc.atten(ADC.ATTN_11DB)

mqtt_client = MQTTClient(MQTT_ID, MQTT_SERVER, user=MQTT_USER, password=MQTT_PASS)

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

# Vibration Helper Function
async def vibrate(duration_sec=2, intensity=1023):
    """
    Activates the vibration motor at the specified intensity for the given duration.

    :param duration_sec: Duration in seconds for which the motor should vibrate.
    :param intensity: PWM duty cycle intensity (0-1023).
    """
    set_vibration(intensity)
    await asyncio.sleep(duration_sec)
    set_vibration(0)

# MQTT Callback
def mqtt_callback(topic, msg):
    try:
        message = msg.decode()
        print("Received message:", message, "on topic:", topic.decode())
        
        # Check if message has a colon, indicating device ID
        if ":" in message:
            if message.split(":")[1] == str(MQTT_ID):
                print("Message is for this device. Processing.")
                
                if message.split(":")[0] == "send_update":
                    print("Requested update. Sending.")
                    calculate_battery_percentage()
                    asyncio.create_task(publish_update())
                elif message.split(":")[0] == "reset":
                    print("Reset command received.")
                    asyncio.create_task(reset_alarm())
                else:
                    print(f"Unknown command for this device: {message}")
            else:
                print(f"Message is not for this device. Ignoring. {message}")
        else:
            print(f"Message does not contain device ID. Ignoring. {message}")

    except Exception as e:
        print(f"Error in MQTT callback: {e}")


# Pulse Sensor Reset Function
def reset_pulse_sensor():
    global pulse_sensor
    pulse_sensor = ADC(Pin(34))
    pulse_sensor.width(ADC.WIDTH_12BIT)
    pulse_sensor.atten(ADC.ATTN_11DB)
    print("Pulse sensor reinitialized.")

# Battery Voltage Reading Function
def read_battery_voltage():
    adc_value = bat_adc.read()
    voltage_at_adc = adc_value * (ADC_VREF / ADC_MAX)
    battery_voltage_raw = voltage_at_adc * (R1 + R2) / R2
    battery_voltage = (battery_voltage_raw * scale_factor) + offset
    return battery_voltage

def calculate_battery_percentage():
    voltage = read_battery_voltage()
    if voltage <= BATTERY_MIN_VOLT:
        return 0
    if voltage >= BATTERY_MAX_VOLT:
        return 100
    battery_message = (voltage - BATTERY_MIN_VOLT) / (BATTERY_MAX_VOLT - BATTERY_MIN_VOLT) * 100
    message = f"BAT:{MQTT_ID}:{battery_message:.1f}"
    mqtt_client.publish(TOPIC_PUB, message.encode())
    print(f"Battery percentage published via MQTT. Voltage: {voltage:.2f}V, Percentage: {battery_message:.1f}%")

# Fall Alarm Timeout Function with Countdown
async def fall_alarm_timeout():
    """
    Waits for 30 seconds. If the alarm is still active after this period,
    sends an MQTT message indicating a fall and stops the alarm.
    Includes a countdown in the console for debugging.
    """
    global fall_alarm_timer, alarm_active  # Declare globals

    for remaining in range(30, 0, -1):
        print(f"Alarm active. {remaining} seconds remaining to reset.")
        await asyncio.sleep(1)  # Wait for 1 second

    if alarm_active:
        message = f"FALD:{MQTT_ID}"
        mqtt_client.publish(TOPIC_PUB, message.encode())
        print("Fall alarm timeout reached. Sending FALD message and stopping alarm.")
        # Directly deactivate the alarm without calling reset_alarm()
        alarm_active = False
        set_vibration(0)
        print("Alarm stopped due to timeout.")
        # Clear the timer reference
        fall_alarm_timer = None

# BPM Measurement Function
async def measure_bpm(duration_sec=30, vibration_duration_sec=2):
    print(f"Starting BPM measurement for {duration_sec} seconds...")

    # Start vibration for vibration_duration_sec seconds at the beginning of measurement
    await vibrate(duration_sec=vibration_duration_sec, intensity=1023)  # Run vibration first

    try:
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
            print(f"Raw sensor value: {sensor_value}")  # Debugging line
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
            print(f"Could not determine BPM. Please try again. (DEBUG:{avg_bpm})")

        # Start vibration for 2 seconds at the end of measurement
        await vibrate(duration_sec=vibration_duration_sec, intensity=500)  # Default duration_sec=2 and intensity=1023

        return avg_bpm

    except Exception as e:
        print(f"Error during BPM measurement: {e}")
        return 0


# Tasks
async def fall_detection_task():
    global alarm_active, fall_alarm_timer
    while True:
        magnitude = read_accel_magnitude()
        # print(f"Accel Magnitude: {magnitude:.2f}")  # Optional debug
        if magnitude > ACCEL_THRESHOLD and not alarm_active:
            alarm_active = True
            print("Fall detected!")
            set_vibration(1023)
            # Start the fall alarm timeout task
            fall_alarm_timer = asyncio.create_task(fall_alarm_timeout())
        if alarm_active and reset_button.value() == 0:
            await reset_alarm()
        await asyncio.sleep_ms(100)

async def reset_alarm():
    global alarm_active, fall_alarm_timer
    if alarm_active:
        alarm_active = False
        set_vibration(0)
        print("Alarm reset.")
        # Cancel the fall alarm timer if it's still running
        if fall_alarm_timer is not None:
            fall_alarm_timer.cancel()
            try:
                await fall_alarm_timer
            except asyncio.CancelledError:
                pass
            fall_alarm_timer = None

async def emergency_button_task():
    """
    Monitors the emergency (help) button with debouncing to prevent multiple triggers.
    """
    last_emergency_press_time = 0  # Initialize last press time
    while True:
        if emergency_button.value() == 0:
            current_time = ticks_ms()
            # Check if enough time has passed since the last press
            if ticks_diff(current_time, last_emergency_press_time) > DEBOUNCE_INTERVAL_MS:
                print("Emergency button pressed! Sending alert.")
                message = f"HELP:{MQTT_ID}"
                mqtt_client.publish(TOPIC_PUB, message.encode())
                last_emergency_press_time = current_time  # Update the last press time
        await asyncio.sleep_ms(50)  # Polling interval (can be adjusted)

async def publish_update():
    
    global bpm_measurement_running
    if bpm_measurement_running:
        print("BPM measurement already running.")
        return
    bpm_measurement_running = True
    try:
        bpm = await measure_bpm()
        if bpm > 0:
            mqtt_client.publish(TOPIC_PUB, f"PULS:{MQTT_ID}:{bpm}".encode())
        else:
            mqtt_client.publish(TOPIC_PUB, f"PULS:{MQTT_ID}:Error".encode())
    finally:
        bpm_measurement_running = False
    print("BPM data published via MQTT.")
    reset_pulse_sensor()  # Reinitialize the pulse sensor
    
async def connect_mqtt():
    while True:
        try:
            mqtt_client.set_callback(mqtt_callback)
            mqtt_client.connect()
            mqtt_client.subscribe(TOPIC_SUB)
            print(f"Connected to MQTT broker. Subscribed to {TOPIC_SUB.decode()}")
            break  # Exit loop on successful connection
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            await asyncio.sleep(5)  # Wait before retrying

# Main
async def main():
    write_mpu6050(0x6B, 0)  # Wake MPU6050

    # Ensure the vibration motor is off at program start
    set_vibration(0)
    print("Vibration motor initialized to OFF.")

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
    #reset()





