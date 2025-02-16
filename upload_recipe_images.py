import os
import requests
import json
import random
import string
from config import MEALIE_URL, HEADERS
from PIL import Image
from requests_toolbelt.multipart.encoder import MultipartEncoder

# Load JSON data from the backup
BACKUP_FILE = "database.json"
MAPPINGS_FILE = "mappings.json"

# Load mappings from mappings.json
if os.path.exists(MAPPINGS_FILE):
    with open(MAPPINGS_FILE, "r", encoding="utf-8") as file:
        MAPPINGS = json.load(file)
        print("🔍 Loaded mappings:", json.dumps(MAPPINGS.get("recipes", {}), indent=2))
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
response = requests.get(f"{MEALIE_URL}/api/recipes", headers=HEADERS)
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
    # Step 1: Get new recipe ID from mappings
    new_recipe_id = MAPPINGS.get("recipes", {}).get(old_name, {}).get("new_id", "")
    
    # Step 2: Use new recipe ID to get the slug
    new_slug = recipe_map.get(new_recipe_id, None)
    
    if not new_slug:
        print(f"⚠ No mapping found for recipe: {old_name}, skipping.")
        continue

    recipe_image_path = os.path.join(IMAGE_FOLDER, old_id, "images")
    if not os.path.exists(recipe_image_path):
        print(f"⚠ No images found for recipe: {new_slug}")
        continue
    
    image_path = os.path.join(recipe_image_path, "original.webp")
    if not os.path.exists(image_path):
        print(f"⚠ No original.webp found for recipe: {new_slug}, skipping.")
        continue
    
    # Convert webp to jpg
    image_path = convert_webp_to_jpg(image_path)
    file_extension = "jpg"
    random_filename = random_string(10)

    print(f"🔍 Preparing to upload: name={random_filename}, slug={new_slug}, extension={file_extension}")

    with open(image_path, "rb") as img_file:
        encoder = MultipartEncoder(
            fields={
                "image": (random_filename + ".jpg", img_file, "image/jpeg"),
                "extension": file_extension
            }
        )
        headers = HEADERS.copy()
        headers["Content-Type"] = encoder.content_type
        
        response = requests.put(
            f"{MEALIE_URL}/api/recipes/{new_slug}/image",
            data=encoder,
            headers=headers,
        )
        print(f"📥 Response: {response.status_code} - {response.text}")
        if response.status_code == 200:
            print(f"✔ Uploaded image for {new_slug}")
        else:
            print(f"❌ Failed to upload image for {new_slug}")

print("✅ Recipe image upload completed!")
