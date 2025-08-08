import os
import requests
import json
import random
import string
from config import MEALIE_URL, HEADERS, MEALIE_VERIFY_SSL
from PIL import Image
from requests_toolbelt.multipart.encoder import MultipartEncoder

# Disable SSL warnings for self-signed certificates only if verification is disabled
import urllib3
if not MEALIE_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load JSON data from the backup
BACKUP_FILE = "database.json"
MAPPINGS_FILE = "mappings.json"

# Load mappings from mappings.json
if os.path.exists(MAPPINGS_FILE):
    with open(MAPPINGS_FILE, "r", encoding="utf-8") as file:
        MAPPINGS = json.load(file)
        print(f"🔍 Loaded recipe mappings: {len(MAPPINGS.get('recipes', {}))} entries")
else:
    print("⚠️ mappings.json not found. Make sure to run create-map.py first.")
    exit(1)

# Load old recipe data to map old ID to name (not slug)
old_recipe_map = {}
if os.path.exists(BACKUP_FILE):
    with open(BACKUP_FILE, "r", encoding="utf-8") as file:
        old_data = json.load(file)
        for recipe in old_data.get("recipes", []):
            old_recipe_map[recipe["id"]] = recipe["name"].lower()  # Use name instead of slug
else:
    print("⚠️ database.json not found! Make sure to provide it.")
    exit(1)

# Fetch new recipes from Mealie to map ID → slug
recipe_map = {}
REQUEST_TIMEOUT = 30
response = requests.get(f"{MEALIE_URL}/api/recipes", headers=HEADERS, verify=MEALIE_VERIFY_SSL, timeout=REQUEST_TIMEOUT)
if response.status_code == 200:
    try:
        for recipe in response.json().get("items", []):
            recipe_map[recipe["id"]] = recipe["slug"]  # Correctly map ID to slug
    except json.JSONDecodeError:
        print("❌ Failed to parse JSON response from API")
        exit(1)
else:
    print(f"❌ Failed to fetch recipes from Mealie API: {response.status_code}")
    exit(1)

# Define path to extracted images
IMAGE_FOLDER = "data/recipes"  # Relative path from project root

# Allowed image formats (including webp)
ALLOWED_IMAGE_FORMATS = ["jpg", "jpeg", "png", "gif", "webp"]

# Convert webp to jpg
def convert_webp_to_jpg(webp_path):
    jpg_path = webp_path.replace(".webp", ".jpg")
    with Image.open(webp_path) as img:
        img = img.convert("RGB")
        img.save(jpg_path, "JPEG")
    return jpg_path

# Generate a random string for file name
def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Upload images
for old_id, old_name in old_recipe_map.items():
    # Step 1: Get new recipe ID from mappings using the old_id instead of name
    new_recipe_id = None
    for recipe_name, mapping_data in MAPPINGS.get("recipes", {}).items():
        if mapping_data.get("old_id") == old_id:
            new_recipe_id = mapping_data.get("new_id")
            break
    
    # Step 2: Use new recipe ID to get the slug
    new_slug = recipe_map.get(new_recipe_id, None)
    
    if not new_slug:
        print(f"⚠ No mapping found for recipe: {old_name} (old_id: {old_id}), skipping.")
        continue

    # Convert old_id to UUID format with hyphens (8-4-4-4-12)
    if len(old_id) == 32 and '-' not in old_id:
        old_id_with_hyphens = f"{old_id[:8]}-{old_id[8:12]}-{old_id[12:16]}-{old_id[16:20]}-{old_id[20:]}"
