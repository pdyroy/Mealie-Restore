import json
import requests
from config import MEALIE_URL, HEADERS, MEALIE_VERIFY_SSL

# Disable SSL warnings for self-signed certificates only if verification is disabled
import urllib3
if not MEALIE_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load JSON data from the backup
BACKUP_FILE = "database.json"  # Ensure this file is in the same folder
with open(BACKUP_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

ingredients = data.get("ingredient_foods", [])

REQUEST_TIMEOUT = 30

# Upload ingredients
for ingredient in ingredients:
    payload = {
        "id": ingredient["id"],
        "name": ingredient["name"],
        "pluralName": ingredient.get("plural_name", ingredient["name"]),
        "description": ingredient.get("description", ""),
        "labelId": ingredient.get("label_id", None),
        "extras": {},
        "aliases": []
    }
    response = requests.post(f"{MEALIE_URL}/api/foods", json=payload, headers=HEADERS, verify=MEALIE_VERIFY_SSL, timeout=REQUEST_TIMEOUT)
    if response.status_code == 201:
        print(f"✔ Successfully added ingredient: {ingredient['name']}")
    elif response.status_code == 409:
        print(f"⚠ Ingredient already exists: {ingredient['name']}")
    else:
        print(f"❌ Failed to add ingredient: {ingredient['name']} - {response.text}")

print("Ingredient upload completed!")
