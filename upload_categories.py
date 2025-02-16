import json
import requests
from config import MEALIE_URL, HEADERS

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
    response = requests.post(f"{MEALIE_URL}/api/organizers/categories", json=payload, headers=HEADERS)
    
    if response.status_code == 201:
        print(f"✔ Successfully added category: {category['name']}")
    elif response.status_code == 409:
        print(f"⚠ Category already exists: {category['name']}")
    else:
        print(f"❌ Failed to add category: {category['name']} - {response.text}")

print("Category upload completed!")
