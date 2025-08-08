import requests
import json
import time
import os
from config import MEALIE_URL, HEADERS, MEALIE_VERIFY_SSL

# Disable SSL warnings for self-signed certificates only if verification is disabled
import urllib3
if not MEALIE_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration for robust connection handling
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# Define file paths
DATABASE_FILE = "database.json"
MAPPINGS_FILE = "mappings.json"

# Load old recipes and instructions from database.json
def fetch_old_data():
    if not os.path.exists(DATABASE_FILE):
        print("⚠️ database.json not found! Make sure to provide it.")
        return {}, {}
    
    with open(DATABASE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    recipes = {recipe["id"]: recipe for recipe in data.get("recipes", [])}
    instructions = {}
    
    for instr in data.get("recipe_instructions", []):
        if instr["recipe_id"] not in instructions:
            instructions[instr["recipe_id"]] = []
        instructions[instr["recipe_id"]].append({
            "id": instr.get("id", ""),
            "title": instr.get("title", ""),
            "summary": instr.get("summary", ""),
            "text": instr.get("text", ""),
            "ingredientReferences": instr.get("ingredientReferences", [])
        })
    
    return recipes, instructions

# Load mappings.json
def load_mappings():
    if not os.path.exists(MAPPINGS_FILE):
        print("⚠️ mappings.json not found! Make sure to provide it.")
        return {}
    
    with open(MAPPINGS_FILE, "r", encoding="utf-8") as file:
        return json.load(file).get("recipes", {})

# Fetch all recipes from Mealie
def fetch_all_recipes():
    recipes = {}
    page = 1
    per_page = 100
    
    while True:
        url = f"{MEALIE_URL}/api/recipes?page={page}&perPage={per_page}"
        response = requests.get(url, headers=HEADERS, verify=MEALIE_VERIFY_SSL, timeout=REQUEST_TIMEOUT)
        print(f"🔄 Fetching recipes: Page {page}, Status Code: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                items = data.get("items", [])
                if not items:
                    break
                for recipe in items:
                    recipes[recipe["slug"]] = recipe
                page += 1
            except requests.exceptions.JSONDecodeError:
                print("❌ Error: Response is not valid JSON!")
                break
        else:
            print(f"⚠️ Failed to fetch recipes: {response.text}")
            break
    return recipes

# Update recipe instructions
def update_recipe_instructions(recipe_slug, instructions):
    url = f"{MEALIE_URL}/api/recipes/{recipe_slug}"
    payload = {"recipeInstructions": instructions}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🔍 Attempt {attempt}/{MAX_RETRIES}: Updating instructions for recipe {recipe_slug}")
            response = requests.patch(url, headers=HEADERS, json=payload, verify=MEALIE_VERIFY_SSL, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                print(f"✅ Successfully updated instructions for recipe: {recipe_slug}")
                return True
            else:
                print(f"❌ Failed to update instructions for recipe {recipe_slug} - {response.text}")
                return False
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
            print(f"⚠️ Connection issue on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                wait_time = attempt * 2
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print(f"❌ Failed to update instructions for recipe {recipe_slug} after {MAX_RETRIES} attempts")
                return False
        except Exception as e:
            print(f"❌ Unexpected error updating instructions for recipe {recipe_slug}: {e}")
            return False

# Main function to update all recipe instructions
def main():
    print("🚀 Starting robust recipe instructions update...")
    old_recipes, old_instructions = fetch_old_data()
    mappings = load_mappings()
    
    if not mappings:
        print("⚠️ No mappings found. Exiting.")
        return
    
    total_recipes = len(mappings)
    processed = 0
    successful = 0
    failed = 0
    
    print(f"📊 Found {total_recipes} recipe mappings to process")
    
    for recipe_name, mapping in mappings.items():
        processed += 1
        old_id = mapping.get("old_id")
        new_id = mapping.get("new_id")
        
        print(f"📋 Progress: {processed}/{total_recipes} - Processing: {recipe_name}")
        
        if old_id:
            try:
                update_recipe_instructions(old_id, new_id, old_instructions)
                successful += 1
                time.sleep(1)  # Small delay between requests
            except Exception as e:
                print(f"❌ Error processing recipe {recipe_name}: {e}")
                failed += 1
        else:
            print(f"⚠️ No old ID found for recipe {recipe_name}, skipping")
            failed += 1
    
    print("\n🎉 Recipe instructions update completed!")
    print(f"📊 Final Results:")
    print(f"✅ Successful updates: {successful}")
    print(f"❌ Failed updates: {failed}")
    print(f"📋 Total processed: {processed}")

if __name__ == "__main__":
    main()
