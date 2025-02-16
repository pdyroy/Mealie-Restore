import requests
import json
import time
import os

# Import Mealie API details from config.py
from config import MEALIE_URL, HEADERS

# Define the database file path
DATABASE_FILE = "database.json"

# Load mappings from mappings.json
MAPPINGS_FILE = "mappings.json"
if os.path.exists(MAPPINGS_FILE):
    with open(MAPPINGS_FILE, "r", encoding="utf-8") as file:
        MAPPINGS = json.load(file)
else:
    print("⚠️ mappings.json not found. Make sure to run create-map.py first.")
    exit(1)

# Load old recipes, users, and nutrition data from database.json
def fetch_old_data():
    if not os.path.exists(DATABASE_FILE):
        print("⚠️ database.json not found! Make sure to provide it.")
        return [], [], {}

    with open(DATABASE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return (
        data.get("recipes", []),
        data.get("users", []),
        {n["recipe_id"]: n for n in data.get("recipe_nutrition", [])}  # Map nutrition by old recipe_id
    )

# Read-only fields that should not be updated
READ_ONLY_FIELDS = {"created_at", "update_at", "date_added", "date_updated", "id", "recipe_id", "group_id"}

# Ensure default values match API expectations
DEFAULT_VALUES = {
    "recipeServings": 0,
    "recipeYieldQuantity": 0,
    "recipeCategory": [],
    "tags": [],
    "tools": [],
    "rating": 0,
    "recipeYield": "",
    "orgURL": "",
    "recipeCuisine": None,
    "lastMade": None,
    "nutrition": {},
    "settings": {
        "public": False,
        "showNutrition": False,
        "showAssets": False,
        "landscapeView": False,
        "disableComments": True,
        "disableAmount": True,
        "locked": False
    },
    "assets": [],
    "notes": [],
    "extras": {},
    "comments": []
}

# Map user ID from old database to new database using username (case-insensitive)
def map_user_id(old_user_id, old_users):
    old_user = next((user for user in old_users if user["id"] == old_user_id), None)
    if old_user:
        username = old_user.get("username", "").lower()  # Normalize username to lowercase
        if username and "users" in MAPPINGS:
            user_mappings = {key.lower(): value["new_id"] for key, value in MAPPINGS["users"].items()}  # Extract only "new_id"
            if username in user_mappings:
                print(f"✅ Mapped user {username} → {user_mappings[username]}")
                return user_mappings[username]
        print(f"⚠️ No mapping found for username: {username}, keeping original user_id.")
    else:
        print(f"⚠️ No matching user found for user_id: {old_user_id}, keeping original.")
    return old_user_id  # Fallback to the old ID if no mapping is found

# Map household ID if present in mappings.json
def map_household_id(old_household_id):
    if "households" in MAPPINGS and old_household_id in MAPPINGS["households"]:
        return MAPPINGS["households"][old_household_id]
    print(f"⚠️ No mapping found for household_id: {old_household_id}, removing field from update.")
    return None  # Return None to exclude it from update payload

# Map nutrition data from old database using recipe mapping
def map_recipe_nutrition(recipe, old_nutrition):
    old_recipe_id = MAPPINGS["recipes"].get(recipe["name"].lower(), {}).get("old_id")
    
    if not old_recipe_id or old_recipe_id not in old_nutrition:
        print(f"⚠️ No nutrition data found for {recipe['name']}, skipping.")
        return {}

    old_nutrition_entry = old_nutrition[old_recipe_id]

    return {
        "calories": old_nutrition_entry.get("calories"),
        "carbohydrateContent": old_nutrition_entry.get("carbohydrate_content"),
        "cholesterolContent": old_nutrition_entry.get("cholesterol_content"),
        "fatContent": old_nutrition_entry.get("fat_content"),
        "fiberContent": old_nutrition_entry.get("fiber_content"),
        "proteinContent": old_nutrition_entry.get("protein_content"),
        "saturatedFatContent": old_nutrition_entry.get("saturated_fat_content"),
        "sodiumContent": old_nutrition_entry.get("sodium_content"),
        "sugarContent": old_nutrition_entry.get("sugar_content"),
        "transFatContent": old_nutrition_entry.get("trans_fat_content"),
        "unsaturatedFatContent": old_nutrition_entry.get("unsaturated_fat_content"),
    }

# Update missing fields based on schema
def update_missing_fields(recipe, old_recipe, old_users, old_nutrition):
    updated_fields = {}
    for key, old_value in old_recipe.items():
        if key in READ_ONLY_FIELDS:
            continue  # Skip read-only fields
        if key == "user_id":
            updated_fields[key] = map_user_id(old_value, old_users)  
        elif key == "household_id":
            mapped_household = map_household_id(old_value)
            if mapped_household:
                updated_fields[key] = mapped_household
        elif key not in recipe or recipe[key] in [None, "", [], 0]:  
            updated_fields[key] = old_value if old_value is not None else DEFAULT_VALUES.get(key, None)
            print(f"🔄 Adding missing field: {key} → {updated_fields[key]}")

    # Add missing nutrition data
    if not recipe.get("nutrition") or recipe["nutrition"] == {}:
        nutrition_data = map_recipe_nutrition(recipe, old_nutrition)
        if nutrition_data:
            updated_fields["nutrition"] = nutrition_data
            print(f"🔄 Adding nutrition data for {recipe['name']} → {nutrition_data}")

    return updated_fields

# Fetch all recipes from Mealie
def fetch_all_recipes():
    recipes = []
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

                recipes.extend(items)
                page += 1

            except requests.exceptions.JSONDecodeError:
                print("❌ Error: Response is not valid JSON!")
                break
        else:
            print(f"⚠️ Failed to fetch recipes: {response.text}")
            break

    return recipes

# Update a recipe in Mealie
def update_recipe(recipe, old_recipes, old_users, old_nutrition):
    old_recipe = next((r for r in old_recipes if r["slug"] == recipe["slug"]), None)
    if not old_recipe:
        print(f"⚠️ No matching old recipe found for: {recipe['name']}")
        return

    print(f"🔍 Old recipe data for {recipe['name']}: {json.dumps(old_recipe, indent=2)}")

    # Only update fields that are missing
    missing_fields = update_missing_fields(recipe, old_recipe, old_users, old_nutrition)
    if not missing_fields:
        print(f"⚠️ No missing fields for {recipe['name']}, skipping update.")
        return

    recipe_slug = recipe["slug"]
    url = f"{MEALIE_URL}/api/recipes/{recipe_slug}"
    print(f"🔍 Sending update with missing fields: {json.dumps(missing_fields, indent=2)}")
    response = requests.patch(url, headers=HEADERS, json=missing_fields)

    if response.status_code == 200:
        print(f"✅ Successfully updated recipe: {recipe['name']}")
    else:
        print(f"❌ Failed to update recipe: {recipe['name']} - {response.text}")

# Main function to update all recipes
def main():
    recipes = fetch_all_recipes()
    old_recipes, old_users, old_nutrition = fetch_old_data()

    if not recipes:
        print("⚠️ No recipes found. Exiting.")
        return

    for recipe in recipes:
        update_recipe(recipe, old_recipes, old_users, old_nutrition)
        time.sleep(1)

    print("✅ Recipe update completed!")

if __name__ == "__main__":
    main()
