from cryptography.fernet import Fernet

# Make a new secret key
key = Fernet.generate_key()
print(f"My secret key is: {key.decode()}")
input("Press Enter to exit...")