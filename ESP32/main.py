
import uasyncio as asyncio
from machine import Pin, I2C, ADC, PWM, reset
from umqttsimple import MQTTClient
from time import ticks_ms, ticks_diff, sleep_ms

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
MQTT_ID = "010101-1111"
mqtt_client = MQTTClient(MQTT_ID, MQTT_SERVER, user=MQTT_USER, password=MQTT_PASS)

# Globals
MPU6050_ADDR = 0x68
ACCEL_THRESHOLD = 2.5
THRESHOLD = 600
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

# MQTT Functions
# def mqtt_callback(topic=TOPIC_SUB, msg):
#     print(f"MQTT Message: {msg.decode()}")
#     if msg.decode() == "reset":
#         asyncio.create_task(reset_alarm())
#     elif msg.decode() == "send_update":
#         asyncio.create_task(publish_update())
#         print("Requested update")

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



async def publish_update():
    bpm = await measure_bpm()
    message = f"{mqtt_client}:{bpm}"
    mqtt_client.publish(TOPIC_PUB, message.encode())

# Tasks
async def fall_detection_task():
    global alarm_active
    while True:
        magnitude = read_accel_magnitude()
        # print(f"Accel Magnitude: {magnitude:.2f}")
        if magnitude > ACCEL_THRESHOLD and not alarm_active:
            alarm_active = True
            print("Fall detected!")
            set_vibration(1023)
        if alarm_active and reset_button.value() == 0:
            await reset_alarm()
        await asyncio.sleep_ms(100)

async def measure_bpm():
    print("Start measuring BPM")
    countdown = 30  # Countdown duration in seconds
    last_beat = 0
    intervals = []
    
    # Display the countdown
    while countdown > 0:
        print(f"Countdown: {countdown} seconds")
        countdown -= 1
        await asyncio.sleep(1)  # Wait for 1 second before updating the countdown
        
    print("Measurement complete, calculating BPM...")
    
    # Now, measure the BPM
    for _ in range(300):
        sensor_value = pulse_sensor.read()
        now = ticks_ms()
        if sensor_value > THRESHOLD and ticks_diff(now, last_beat) > MIN_BEAT_INTERVAL:
            if last_beat > 0:
                intervals.append(ticks_diff(now, last_beat))
            last_beat = now
        await asyncio.sleep_ms(100)
    
    # Calculate BPM if enough intervals were recorded
    if len(intervals) > 1:
        bpm = round(60000 / (sum(intervals) / len(intervals)), 1)
        print(f"BPM: {bpm}")
        return bpm
    
    print("Not enough data to calculate BPM.")
    return 0


async def reset_alarm():
    global alarm_active
    alarm_active = False
    set_vibration(0)
    print("Alarm reset.")

async def emergency_button_task():
    while True:
        if emergency_button.value() == 0:
            print("Emergency button pressed! Sending alert.")
            mqtt_client.publish(TOPIC_PUB, "Emergency Alert!")
        await asyncio.sleep_ms(100)

async def connect_mqtt():
    mqtt_client.set_callback(mqtt_callback)
    mqtt_client.connect()
    mqtt_client.subscribe(TOPIC_SUB)
    print(f"Connected to MQTT broker {TOPIC_SUB}")

# Main
async def main():
    write_mpu6050(0x6B, 0)  # Wake MPU6050
    try:
        await connect_mqtt()
    except Exception as e:
        print(f"Error MQTT : {e}")
    
    asyncio.create_task(fall_detection_task())
    asyncio.create_task(emergency_button_task())
    
    # Main loop to process incoming MQTT messages
    while True:
        mqtt_client.check_msg()  # Ensure this is called to process messages
        await asyncio.sleep(1)


try:
    asyncio.run(main())
except Exception as e:
    print(f"Error: {e}")
    #reset()



