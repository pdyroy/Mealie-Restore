import requests
import json
import time
import os
from config import MEALIE_URL, HEADERS

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
        response = requests.get(url, headers=HEADERS)
        
        if response.status_code != 200:
            print(f"⚠️ Failed to fetch recipes: {response.text}")
            break
        
        data = response.json()
        items = data.get("items", [])
        
        if not items:
            break
        
        for recipe in items:
            recipes[recipe["id"]] = recipe
        
        page += 1
    
    return recipes

# Update recipe instructions
def update_recipe_instructions(old_recipe_id, new_recipe_id, old_instructions):
    if old_recipe_id not in old_instructions:
        print(f"⚠️ No instructions found for old recipe ID {old_recipe_id}, skipping.")
        return
    
    if new_recipe_id is None:
        print(f"⚠️ No new ID found for old recipe ID {old_recipe_id}, skipping.")
        return
    
    formatted_instructions = [
        {
            "id": instr.get("id", ""),
            "title": instr.get("title", ""),
            "summary": instr.get("summary", ""),
            "text": instr.get("text", ""),
            "ingredientReferences": instr.get("ingredientReferences", [])
        }
        for instr in old_instructions[old_recipe_id]
    ]
    
    payload = {"recipeInstructions": formatted_instructions}
    url = f"{MEALIE_URL}/api/recipes/{new_recipe_id}"
    
    print(f"🔄 Updating instructions for old recipe ID {old_recipe_id} → new recipe ID {new_recipe_id}")
    print(f"📦 Payload being sent: {json.dumps(payload, indent=2)}")
    response = requests.patch(url, headers=HEADERS, json=payload)
    
    if response.status_code == 200:
        print(f"✅ Successfully updated instructions for recipe ID {new_recipe_id}")
    else:
        print(f"❌ Failed to update instructions for recipe ID {new_recipe_id} - {response.text}")

# Main function to update all recipe instructions
def main():
    old_recipes, old_instructions = fetch_old_data()
    mappings = load_mappings()
    
    if not mappings:
        print("⚠️ No mappings found. Exiting.")
        return
    
    for recipe_name, mapping in mappings.items():
        old_id = mapping.get("old_id")
        new_id = mapping.get("new_id")
        
        if old_id:
            update_recipe_instructions(old_id, new_id, old_instructions)
            time.sleep(1)
    
    print("✅ Recipe instructions update completed!")

if __name__ == "__main__":
    main()
