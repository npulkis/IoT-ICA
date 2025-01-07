import threading
import time
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback
from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO
from dotenv import load_dotenv

LED_PINS = [3, 5, 7]
GPIO.setmode(GPIO.BOARD)
for pin in LED_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

load_dotenv()

pnconfig = PNConfiguration()
pnconfig.subscribe_key = os.getenv('PUBNUB_SUBSCRIBE_KEY')
pnconfig.publish_key = os.getenv('PUBNUB_PUBLISH_KEY')
pnconfig.user_id = os.getenv('PUBNUB_PI_ID')
pubnub = PubNub(pnconfig)

reader = SimpleMFRC522()

MODE = "scan"  

def card_scanner():
    try:
        while True:
            print(f"Current mode: {MODE}. Waiting for card scan...")
            card_id, _ = reader.read()
            print(f"Card scanned: {card_id}")

            if MODE == "register":
                print("Publishing to card_register channel...")
                pubnub.publish().channel("card_register").message({"rfid_card_id": card_id}).sync()
            elif MODE == "scan":
                print("Publishing to card_scan channel...")
                pubnub.publish().channel("card_scan").message({"rfid_card_id": card_id}).sync()

            time.sleep(2)
    except KeyboardInterrupt:
        print("Card scanning stopped.")
    finally:
        GPIO.cleanup()

class PiSubscribeCallback(SubscribeCallback):
    def message(self, pubnub, message):
        global MODE
        data = message.message
        print(f"Received PubNub message: {data}")

        if "mode" in data:
            new_mode = data.get("mode")
            if new_mode in ["register", "scan"]:
                MODE = new_mode
                print(f"Mode updated to: {MODE}")
            else:
                print(f"Invalid mode received: {new_mode}")

        elif "led_number" in data and "action" in data:
            led_number = data.get("led_number")
            action = data.get("action")
            try:
                led_index = int(led_number) - 1
                if 0 <= led_index < len(LED_PINS):
                    GPIO.output(LED_PINS[led_index], GPIO.HIGH if action == "on" else GPIO.LOW)
                    print(f"LED {led_number} turned {action}")
                else:
                    print(f"Invalid LED number: {led_number}")
            except ValueError as e:
                print(f"Error controlling LED: {e}")
        else:
            print("Unrecognized message format.")

pubnub.add_listener(PiSubscribeCallback())
pubnub.subscribe().channels(["led_control", "mode_control"]).execute()

scanner_thread = threading.Thread(target=card_scanner)
scanner_thread.daemon = True
scanner_thread.start()

try:
    print("Starting Raspberry Pi script...")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")
finally:
    print("Cleaning up GPIO pins...")
    GPIO.cleanup()
