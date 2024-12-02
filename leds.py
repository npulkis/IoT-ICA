import RPi.GPIO as GPIO
import time

LED_PINS = [3, 5, 7, 11]  # Replace with your actual GPIO pins

GPIO.setmode(GPIO.BOARD)
for pin in LED_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)  # Turn off all LEDs initially

try:
    while True:
        for pin in LED_PINS:
            print(f"Turning on LED connected to pin {pin}")
            GPIO.output(pin, GPIO.HIGH)  # Turn LED on
            time.sleep(1)
            GPIO.output(pin, GPIO.LOW)  # Turn LED off
except KeyboardInterrupt:
    print("Exiting...")
finally:
    GPIO.cleanup()
