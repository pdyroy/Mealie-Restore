import json
import requests
import time
from config import MEALIE_URL, HEADERS, MEALIE_VERIFY_SSL

REQUEST_TIMEOUT = 30

# Disable SSL warnings for self-signed certificates only if verification is disabled
import urllib3
if not MEALIE_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load JSON data from the backup
BACKUP_FILE = "database.json"
with open(BACKUP_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

recipes = data.get("recipes", [])

# Store recipe mappings
created_recipes = {}

# Step 1: Upload recipes
for recipe in recipes:
    payload = {"name": recipe["name"]}
    response = requests.post(f"{MEALIE_URL}/api/recipes", json=payload, headers=HEADERS, verify=MEALIE_VERIFY_SSL, timeout=REQUEST_TIMEOUT)

    if response.status_code == 201:
        recipe_slug = response.json()
        created_recipes[recipe["id"]] = recipe_slug
        print(f"✔ Successfully created recipe: {recipe['name']} ({recipe_slug})")
    elif response.status_code == 409:
        print(f"⚠ Recipe already exists: {recipe['name']}")
    else:
        print(f"❌ Failed to create recipe: {recipe['name']} - {response.text}")

    # Small delay to prevent API rate limits
    time.sleep(1)

print("Recipe creation completed!")
