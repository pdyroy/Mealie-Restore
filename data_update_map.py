import requests
import json
import time
import os
from config import MEALIE_URL, HEADERS, MEALIE_VERIFY_SSL

# Disable SSL warnings for self-signed certificates only if verification is disabled
import urllib3
if not MEALIE_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Define file paths
DATABASE_FILE = "database.json"
MAPPINGS_FILE = "mappings.json"
REQUEST_TIMEOUT = 30

# Load old data from database.json
def fetch_old_data(entity, key="name"):
    if not os.path.exists(DATABASE_FILE):
        print(f"⚠️ {DATABASE_FILE} not found! Make sure to provide it.")
        return {}
    
    with open(DATABASE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    # Handle different entity structures
    if entity == "foods":
        return {item["name"].lower(): {"old_id": item["id"], "new_id": None} for item in data.get("ingredient_foods", []) if "name" in item and "id" in item}
    elif entity == "units":
        return {item["name"].lower(): {"old_id": item["id"], "new_id": None} for item in data.get("ingredient_units", []) if "name" in item and "id" in item}
    elif entity == "tools":
        return {item["name"].lower(): {"old_id": item["id"], "new_id": None} for item in data.get("tools", []) if "name" in item and "id" in item}
    elif entity == "categories":
        return {item["name"].lower(): {"old_id": item["id"], "new_id": None} for item in data.get("categories", []) if "name" in item and "id" in item}
    elif entity == "tags":
        return {item["name"].lower(): {"old_id": item["id"], "new_id": None} for item in data.get("tags", []) if "name" in item and "id" in item}
    elif entity == "users":
        return {item["username"].lower(): {"old_id": item["id"], "new_id": None} for item in data.get("users", []) if "username" in item and "id" in item}
    else:
        return {item[key].lower(): {"old_id": item["id"], "new_id": None} for item in data.get(entity, []) if key in item and "id" in item}

# Fetch all recipes and other entities from Mealie and store their names and new IDs
def fetch_new_data(entity, key="name"):
    items = {}
    page = 1
    per_page = 100
    
    while True:
        url = f"{MEALIE_URL}/api/{entity}?page={page}&perPage={per_page}"
        print(f"📡 Fetching: {url}")
        response = requests.get(url, headers=HEADERS, verify=MEALIE_VERIFY_SSL, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            print(f"❌ Error fetching {entity}: {response.status_code}")
            break
        
        data = response.json()
        if "items" in data:
            for item in data["items"]:
                if key in item and "id" in item:
                    items[item[key].lower()] = {"old_id": None, "new_id": item["id"]}
                else:
                    print(f"⚠️ Skipping entry in {entity} without '{key}' or 'id': {item}")
        else:
            print(f"⚠️ Unexpected response format for {entity}: {data}")
            break
        
        if not data.get("next"):
            break
        page += 1
    
    return items

# Generate mappings for recipes, foods, units, tools, categories, tags, and users
def generate_mappings():
    mappings = {}
    entities = [
        ("recipes", "name"),
        ("foods", "name"),
        ("units", "name"),
        ("organizers/tools", "name"),
        ("organizers/categories", "name"),
        ("organizers/tags", "name"),
        ("admin/users", "username")  # Use username for users
    ]
    
    for entity, key in entities:
        old_data = fetch_old_data(entity.split("/")[-1], key)
        new_data = fetch_new_data(entity, key)
        
        # Merge old and new IDs
        for name, details in old_data.items():
            if name in new_data:
                new_data[name]["old_id"] = details["old_id"]
            else:
                new_data[name] = details  # Keep old data if no match in new
        
        mappings[entity.split("/")[-1]] = new_data
        time.sleep(1)  # Avoid rate-limiting
    
    # Save mappings to a JSON file
    with open(MAPPINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(mappings, f, indent=4)
    print("✅ Mappings saved to mappings.json")

# Main function
def main():
    print("🚀 Starting Mealie Data Mapping...")
    generate_mappings()
    print("✅ Mapping complete!")

if __name__ == "__main__":
    main()
