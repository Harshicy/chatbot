from dotenv import load_dotenv
import os

# Explicitly load the .env file
loaded = load_dotenv('.env')
print(f"Dotenv loaded: {loaded}")  # Should print True
api_key = os.getenv("WEATHER_API_KEY")
print(f"API_KEY from test: {api_key}")  # Should print your key
print(f"All env vars: {dict(os.environ)}")  # Debug all environment variables
if not api_key:
    print("Warning: Could not load API_KEY. Check file format or permissions.")