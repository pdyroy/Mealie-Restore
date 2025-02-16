import requests
import json
import os
import uuid
from config import MEALIE_URL, HEADERS

# Load mappings from mappings.json
def load_mappings():
    MAPPINGS_FILE = "mappings.json"
    if not os.path.exists(MAPPINGS_FILE):
        print("⚠️ mappings.json not found. Make sure to generate it.")
        return {}
    
    with open(MAPPINGS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

# Load old database from database.json
def load_old_database():
    DATABASE_FILE = "database.json"
    if not os.path.exists(DATABASE_FILE):
        print("⚠️ database.json not found. Make sure to provide it.")
        return {}, []
    
    with open(DATABASE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    recipes = {recipe["id"]: recipe for recipe in data.get("recipes", [])}
    ingredients = data.get("recipes_ingredients", [])
    return recipes, ingredients

# Fetch all recipes from Mealie
def fetch_all_recipes():
    recipes = {}
    page = 1
    per_page = 100
    
    while True:
        url = f"{MEALIE_URL}/api/recipes?page={page}&perPage={per_page}"
        response = requests.get(url, headers=HEADERS)
        
        print(f"🔄 Fetching recipes: Page {page}, Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    break
                
                for recipe in items:
                    recipes[recipe["slug"]] = recipe  # Use slug instead of ID
                
                page += 1
            except requests.exceptions.JSONDecodeError:
                print("❌ Error: Response is not valid JSON!")
                break
        else:
            print(f"⚠️ Failed to fetch recipes: {response.text}")
            break
    
    return recipes

# Construct ingredients in the required format
def construct_ingredient_payload(old_ingr, unit_mappings, food_mappings):
    ingredients = []
    
    for ingr in old_ingr:
        unit_entry = next((u for u in unit_mappings.values() if u.get("old_id") == ingr.get("unit_id")), {})
        food_entry = next((f for f in food_mappings.values() if f.get("old_id") == ingr.get("food_id")), {})

        unit_id = unit_entry.get("new_id")
        unit_name = next((name for name, u in unit_mappings.items() if u.get("old_id") == ingr.get("unit_id")), None)

        food_id = food_entry.get("new_id")
        food_name = next((name for name, f in food_mappings.items() if f.get("old_id") == ingr.get("food_id")), None)

        note = ingr.get("note", "").strip()
        quantity = ingr.get("quantity", 1.0)  # Default to 1.0 if missing
        reference_id = ingr.get("reference_id", str(uuid.uuid4()))
        original_text = ingr.get("original_text", "")

        # Construct a properly formatted display field
        display_parts = []
        if quantity:
            display_parts.append(str(quantity))
        if unit_name:
            display_parts.append(unit_name)
        if food_name:
            display_parts.append(food_name)
        if note:
            display_parts.append(f"({note})")  # Wrap note in brackets for readability

        display = " ".join(display_parts).strip()

        # Ensure `id` and `name` fields are correctly included
        ingredient_payload = {
            "quantity": quantity,
            "unit": {"id": unit_id, "name": unit_name} if unit_id else None,
            "food": {"id": food_id, "name": food_name} if food_id else None,
            "note": note if note else None,
            "isFood": bool(food_id),
            "disableAmount": False,  # <-- Ensures ingredient amounts are visible
            "display": display,
            "referenceId": reference_id,
            "originalText": original_text if original_text else None
        }

        # Remove unnecessary fields for cleaner JSON
        ingredient_payload = {k: v for k, v in ingredient_payload.items() if v is not None}

        ingredients.append(ingredient_payload)

    return ingredients


# Send updated ingredients to Mealie
def update_recipe_ingredients(recipe_slug, ingredients):
    url = f"{MEALIE_URL}/api/recipes/{recipe_slug}"
    payload = {"recipeIngredient": ingredients}

    print(f"🔍 Sending updated ingredients for {recipe_slug}")
    print(json.dumps(payload, indent=4))  # Log the payload before sending

    response = requests.patch(url, headers=HEADERS, json=payload)
    if response.status_code == 200:
        print(f"✅ Successfully updated ingredients for recipe: {recipe_slug}")
    else:
        print(f"❌ Failed to update ingredients for recipe {recipe_slug} - {response.text}")

# Process recipes and update their ingredients
def process_recipe_updates():
    mappings = load_mappings()
    old_recipes, old_ingredients = load_old_database()
    new_recipes = fetch_all_recipes()

    if not new_recipes:
        print("⚠️ No recipes found. Exiting.")
        return

    recipe_mappings = mappings.get("recipes", {})
    unit_mappings = mappings.get("units", {})
    food_mappings = mappings.get("foods", {})

    for recipe_slug, recipe in new_recipes.items():
        old_recipe_id = next((mapping["old_id"] for old_name, mapping in recipe_mappings.items() if mapping.get("new_id") == recipe["id"]), None)

        if old_recipe_id:
            old_ingr = [ingr for ingr in old_ingredients if str(ingr["recipe_id"]) == str(old_recipe_id)]
            if old_ingr:
                parsed_ingredients = construct_ingredient_payload(old_ingr, unit_mappings, food_mappings)
                if parsed_ingredients:
                    update_recipe_ingredients(recipe_slug, parsed_ingredients)

if __name__ == "__main__":
    process_recipe_updates()
