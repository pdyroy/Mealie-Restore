
import json
import requests
from config import MEALIE_URL, HEADERS

# Load JSON data from the backup
BACKUP_FILE = "database.json"  # Ensure this file is in the same folder
with open(BACKUP_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

tags = data.get("tags", [])

# Upload tags
for tag in tags:
    payload = {
        "name": tag["name"]
    }
    response = requests.post(f"{MEALIE_URL}/api/organizers/tags", json=payload, headers=HEADERS)
    
    if response.status_code == 201:
        print(f"✔ Successfully added tag: {tag['name']}")
    elif response.status_code == 409:
        print(f"⚠ Tag already exists: {tag['name']}")
    else:
        print(f"❌ Failed to add tag: {tag['name']} - {response.text}")

print("Tag upload completed!")
