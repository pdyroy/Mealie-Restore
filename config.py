import os
from dotenv import load_dotenv

load_dotenv()

MEALIE_URL = os.getenv("MEALIE_URL")
API_TOKEN = os.getenv("API_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}
