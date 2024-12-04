from machine import Pin, I2C

# Pin Definitions
temperature_pin = 4 # DS18B20 an GPIO 4
imu_sda_pin = 21 # SDA an GPIO 21
imu_scl_pin = 22 # SCL an GPIO 22
puls_pin = 34
vibration_motor_pin = 33
buzzer_pin = 27
battery_voltage_pin = 32

# Pin Objects
puls_sensor = Pin(puls_pin, Pin.IN)
vibration_motor = Pin(vibration_motor_pin, Pin.OUT)
buzzer_pin = Pin(buzzer_pin, Pin.OUT)
battery_voltage = Pin(battery_voltage_pin, Pin.IN)
temperature_sensor = Pin(temperature_pin, Pin.IN) # DS18B20 an GPIO 4
imu_sda = Pin(imu_sda_pin, Pin.OUT) # SDA an GPIO 21
imu_scl = Pin(imu_scl_pin, Pin.OUT) # SCL an GPIO 22
imu_i2c = I2C(scl=imu_scl, sda=imu_sda, freq=100000) # I2C Bus
imu_i2c.scan()

