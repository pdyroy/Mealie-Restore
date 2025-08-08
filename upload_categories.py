import json
import requests
from config import MEALIE_URL, HEADERS, MEALIE_VERIFY_SSL

# Disable SSL warnings for self-signed certificates only if verification is disabled
import urllib3
if not MEALIE_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 30

# Load JSON data from the backup
BACKUP_FILE = "database.json"  # Ensure this file is in the same folder
with open(BACKUP_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

categories = data.get("categories", [])

# Upload categories
for category in categories:
    payload = {
        "name": category["name"]
    }
    response = requests.post(f"{MEALIE_URL}/api/organizers/categories", json=payload, headers=HEADERS, verify=MEALIE_VERIFY_SSL, timeout=REQUEST_TIMEOUT)
    
    if response.status_code == 201:
        print(f"✔ Successfully added category: {category['name']}")
    elif response.status_code == 409:
        print(f"⚠ Category already exists: {category['name']}")
    else:
        print(f"❌ Failed to add category: {category['name']} - {response.text}")

print("Category upload completed!")
