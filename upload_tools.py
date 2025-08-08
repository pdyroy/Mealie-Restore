import json
import requests
from config import MEALIE_URL, HEADERS, MEALIE_VERIFY_SSL

# Load JSON data from the backup
BACKUP_FILE = "database.json"  # Ensure this file is in the same folder
with open(BACKUP_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

tools = data.get("tools", [])

# Upload tools
for tool in tools:
    payload = {
        "name": tool["name"],
        "householdsWithTool": []
    }
    response = requests.post(f"{MEALIE_URL}/api/organizers/tools", json=payload, headers=HEADERS, verify=MEALIE_VERIFY_SSL)
    
    if response.status_code == 201:
        print(f"✔ Successfully added tool: {tool['name']}")
    elif response.status_code == 409:
        print(f"⚠ Tool already exists: {tool['name']}")
    else:
        print(f"❌ Failed to add tool: {tool['name']} - {response.text}")

print("Tool upload completed!")
