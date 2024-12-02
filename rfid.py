from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO

reader = SimpleMFRC522()


try:
    # # Writing to the card
    # print("Place your card near the reader to write...")
    # text_to_write = "test"
    # reader.write(text_to_write)
    # print(f"Written '{text_to_write}' to the card.")

    # Reading from the card
    print("Place your card near the reader to read...")
    card_id, text_read = reader.read()
    print(f"Card ID: {card_id}")
    print(f"Data on card: {text_read}")

finally:
    GPIO.cleanup()
