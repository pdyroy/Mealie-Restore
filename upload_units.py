import json
import requests
from config import MEALIE_URL, HEADERS, MEALIE_VERIFY_SSL

# Load JSON data from the backup
BACKUP_FILE = "database.json"  # Ensure this file is in the same folder
with open(BACKUP_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

units = data.get("ingredient_units", [])

# Upload ingredient units
for unit in units:
    payload = {
        "id": unit["id"],
        "name": unit["name"],
        "pluralName": unit.get("plural_name", unit["name"]),
        "description": unit.get("description", ""),
        "abbreviation": unit.get("abbreviation", ""),
        "pluralAbbreviation": unit.get("plural_abbreviation", ""),
        "useAbbreviation": unit.get("use_abbreviation", False),
        "fraction": unit.get("fraction", True),
        "extras": {},
        "aliases": []
    }
    response = requests.post(f"{MEALIE_URL}/api/units", json=payload, headers=HEADERS, verify=MEALIE_VERIFY_SSL)
    if response.status_code == 201:
        print(f"✔ Successfully added unit: {unit['name']}")
    elif response.status_code == 409:
        print(f"⚠ Unit already exists: {unit['name']}")
    else:
        print(f"❌ Failed to add unit: {unit['name']} - {response.text}")

print("Ingredient units upload completed!")

