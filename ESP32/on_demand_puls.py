# Simplified PulseSensor Reader for ESP32 using MicroPython
# Allows manual BPM measurement via REPL with a countdown display

import time
from machine import ADC, Pin

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

# Instructions for REPL Interaction
print("PulseSensor Reader Initialized.")
print("To measure BPM, call the 'measure_bpm()' function with desired duration in seconds.")
print("Example: average_bpm = measure_bpm(30)")

