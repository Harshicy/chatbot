from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os

# Get the secret key from .env
load_dotenv()
FERNET_KEY = os.environ.get('FERNET_KEY')
if not FERNET_KEY:
    print("Oops! Add your secret key to .env first!")
    input("Press Enter to exit...")
    exit()
cipher = Fernet(FERNET_KEY.encode())

# Your WeatherAPI key
api_key = "e5262cf0d632f4cd200aa96e1803fbcb"

# Lock the API key
locked_key = cipher.encrypt(api_key.encode())

# Save the locked key
with open('config.enc', 'wb') as f:
    f.write(locked_key)

print(f"Locked key saved to config.enc: {locked_key.decode()}")
input("Press Enter to exit...")