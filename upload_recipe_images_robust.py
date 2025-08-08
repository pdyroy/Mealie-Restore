import os
import requests
import json
import random
import string
import time
from config import MEALIE_URL, HEADERS, MEALIE_VERIFY_SSL
from PIL import Image
from requests_toolbelt.multipart.encoder import MultipartEncoder

# Disable SSL warnings for self-signed certificates only if verification is disabled
import urllib3
if not MEALIE_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration for robust uploading
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 30  # seconds
DELAY_BETWEEN_UPLOADS = 1  # seconds

# Load JSON data from the backup
BACKUP_FILE = "database.json"
MAPPINGS_FILE = "mappings.json"

def load_mappings():
    """Load mappings from mappings.json"""
    if os.path.exists(MAPPINGS_FILE):
        with open(MAPPINGS_FILE, "r", encoding="utf-8") as file:
            mappings = json.load(file)
            print(f"🔍 Loaded recipe mappings: {len(mappings.get('recipes', {}))} entries")
            return mappings
    else:
        print("⚠️ mappings.json not found. Make sure to run create-map.py first.")
        exit(1)

def load_old_recipes():
    """Load old recipe data to map old ID to name"""
    old_recipe_map = {}
    if os.path.exists(BACKUP_FILE):
        with open(BACKUP_FILE, "r", encoding="utf-8") as file:
            old_data = json.load(file)
            for recipe in old_data.get("recipes", []):
                old_recipe_map[recipe["id"]] = recipe["name"].lower()
            print(f"📚 Loaded {len(old_recipe_map)} old recipes")
            return old_recipe_map
    else:
        print("⚠️ database.json not found! Make sure to provide it.")
        exit(1)

def fetch_new_recipes():
    """Fetch new recipes from Mealie to map ID → slug"""
    recipe_map = {}
    page = 1
    per_page = 100
    
    while True:
        try:
            response = requests.get(
                f"{MEALIE_URL}/api/recipes?page={page}&perPage={per_page}", 
                headers=HEADERS, 
                verify=MEALIE_VERIFY_SSL,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    break
                    
                for recipe in items:
                    recipe_map[recipe["id"]] = recipe["slug"]
                
                page += 1
                print(f"📡 Fetched page {page-1} with {len(items)} recipes")
                
            else:
                print(f"❌ Failed to fetch recipes from Mealie API: {response.status_code}")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching recipes: {e}")
            break
    
    print(f"🎯 Total recipes fetched: {len(recipe_map)}")
    return recipe_map

def convert_webp_to_jpg(webp_path):
    """Convert webp to jpg"""
    jpg_path = webp_path.replace(".webp", ".jpg")
    try:
        with Image.open(webp_path) as img:
            img = img.convert("RGB")
            img.save(jpg_path, "JPEG", quality=90)
        return jpg_path
    except Exception as e:
        print(f"❌ Error converting WebP to JPG: {e}")
        return None

def random_string(length=10):
    """Generate a random string for file name"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def upload_image_with_retry(new_slug, image_path, max_retries=MAX_RETRIES):
    """Upload image with retry logic"""
    file_extension = "jpg"
    random_filename = random_string(10)
    
    for attempt in range(max_retries):
        try:
            print(f"🔍 Attempt {attempt + 1}/{max_retries}: Uploading image for {new_slug}")
            
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
                    verify=MEALIE_VERIFY_SSL,
                    timeout=REQUEST_TIMEOUT
                )
                
                print(f"📥 Response: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"✅ Successfully uploaded image for {new_slug}")
                    return True
                else:
                    print(f"⚠️ Upload failed with status {response.status_code}: {response.text}")
                    
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout, 
                urllib3.exceptions.ProtocolError) as e:
            print(f"🔄 Connection error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Waiting {RETRY_DELAY} seconds before retry...")
                time.sleep(RETRY_DELAY)
            
        except Exception as e:
            print(f"❌ Unexpected error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
    
    print(f"❌ Failed to upload image for {new_slug} after {max_retries} attempts")
    return False

def main():
    """Main function to upload all recipe images"""
    print("🚀 Starting robust recipe image upload...")
    
    # Load data
    mappings = load_mappings()
    old_recipe_map = load_old_recipes()
    recipe_map = fetch_new_recipes()
    
    # Define path to extracted images
    IMAGE_FOLDER = "data/recipes"
    
    # Track progress
    total_recipes = len(old_recipe_map)
    successful_uploads = 0
    failed_uploads = 0
    skipped_recipes = 0
    
    print(f"🎯 Processing {total_recipes} recipes...")
    
    for i, (old_id, old_name) in enumerate(old_recipe_map.items(), 1):
        print(f"\n📋 Progress: {i}/{total_recipes} - Processing: {old_name}")
        
        # Step 1: Get new recipe ID from mappings using the old_id
        new_recipe_id = None
        for recipe_name, mapping_data in mappings.get("recipes", {}).items():
            if mapping_data.get("old_id") == old_id:
                new_recipe_id = mapping_data.get("new_id")
                break
        
        # Step 2: Use new recipe ID to get the slug
        new_slug = recipe_map.get(new_recipe_id, None)
        
        if not new_slug:
            print(f"⚠️ No mapping found for recipe: {old_name} (old_id: {old_id}), skipping.")
            skipped_recipes += 1
            continue

        # Convert old_id to UUID format with hyphens (8-4-4-4-12)
        if len(old_id) == 32 and '-' not in old_id:
            old_id_with_hyphens = f"{old_id[:8]}-{old_id[8:12]}-{old_id[12:16]}-{old_id[16:20]}-{old_id[20:]}"
        else:
            old_id_with_hyphens = old_id
        
        recipe_image_path = os.path.join(IMAGE_FOLDER, old_id_with_hyphens, "images")
        if not os.path.exists(recipe_image_path):
            print(f"⚠️ No images found for recipe: {new_slug}")
            skipped_recipes += 1
            continue
        
        image_path = os.path.join(recipe_image_path, "original.webp")
        if not os.path.exists(image_path):
            print(f"⚠️ No original.webp found for recipe: {new_slug}, skipping.")
            skipped_recipes += 1
            continue
        
        # Convert webp to jpg
        converted_image_path = convert_webp_to_jpg(image_path)
        if not converted_image_path:
            print(f"❌ Failed to convert image for recipe: {new_slug}")
            failed_uploads += 1
            continue
        
        # Upload with retry logic
        if upload_image_with_retry(new_slug, converted_image_path):
            successful_uploads += 1
        else:
            failed_uploads += 1
        
        # Cleanup converted file
        try:
            if os.path.exists(converted_image_path):
                os.remove(converted_image_path)
        except Exception as e:
            print(f"⚠️ Failed to cleanup converted file: {e}")
        
        # Add delay between uploads to be gentle on the server
        if i < total_recipes:
            time.sleep(DELAY_BETWEEN_UPLOADS)
    
    # Final summary
    print(f"\n🎉 Upload completed!")
    print(f"✅ Successful uploads: {successful_uploads}")
    print(f"❌ Failed uploads: {failed_uploads}")
    print(f"⚠️ Skipped recipes: {skipped_recipes}")
    print(f"📊 Total processed: {successful_uploads + failed_uploads + skipped_recipes}")

if __name__ == "__main__":
    main()
