import json
import requests
from config import MEALIE_URL, HEADERS

# Load JSON data from the backup
BACKUP_FILE = "database.json"  # Ensure this file is in the same folder
with open(BACKUP_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

users = data.get("users", [])

# Default password for new users (change if needed)
DEFAULT_PASSWORD = "ChangeMe123!"

# Predefined Group and Household IDs
DEFAULT_GROUP_ID = "Home"  # Home Group
DEFAULT_HOUSEHOLD = "Family"  # Default Household Name

# Upload users
for user in users:
    payload = {
        "admin": user.get("admin", False),
        "email": user["email"],
        "fullName": user.get("fullName", user["username"]),
        "group": DEFAULT_GROUP_ID,
        "household": DEFAULT_HOUSEHOLD,
        "username": user["username"],
        "password": DEFAULT_PASSWORD  # Required field
    }
    response = requests.post(f"{MEALIE_URL}/api/admin/users", json=payload, headers=HEADERS)
    
    if response.status_code == 201:
        print(f"✔ Successfully added user: {user['username']}")
    elif response.status_code == 409:
        print(f"⚠ User already exists: {user['username']}")
    else:
        print(f"❌ Failed to add user: {user['username']} - {response.text}")

print("User upload completed!")
