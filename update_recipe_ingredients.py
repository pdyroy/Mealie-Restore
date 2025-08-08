import requests
import json
import os
import uuid
import time
import re
import argparse
from config import MEALIE_URL, HEADERS, OPENROUTER_URL, OPENROUTER_MODEL, get_openrouter_headers, MEALIE_VERIFY_SSL

# Disable SSL warnings only when verification is disabled (opt-in via env)
import urllib3
if not MEALIE_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration for robust connection handling
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# --- OpenRouter setup ---
OPENROUTER_HEADERS = get_openrouter_headers()
PARSER_CACHE: dict[str, dict] = {}

# Small map of common German unit synonyms to canonical names used in Mealie
UNIT_SYNONYMS = {
    "el": "Esslöffel",
    "essloeffel": "Esslöffel",
    "esslöffel": "Esslöffel",
    "tbsp": "Esslöffel",
    "tl": "Teelöffel",
    "teeloeffel": "Teelöffel",
    "teelöffel": "Teelöffel",
    "tsp": "Teelöffel",
    "g": "Gramm",
    "gram": "Gramm",
    "gr": "Gramm",
    "kg": "Kilogramm",
    "kilogramm": "Kilogramm",
    "ml": "Milliliter",
    "milliliter": "Milliliter",
    "l": "Liter",
    "liter": "Liter",
    "prise": "Prise",
    "stk": "Stück",
    "stück": "Stück",
}

# Extend unit synonyms (normalized keys)
UNIT_SYNONYMS.update({
    "gramm": "Gramm",
    "millilitre": "Milliliter",
    "milliliter": "Milliliter",
    "milliliters": "Milliliter",
    "teaspoon": "Teelöffel",
    "tablespoon": "Esslöffel",
    # New: cloves of garlic
    "zehe": "Zehe",
    "zehen": "Zehe",
})

# --- Helpers ---
def _normalize(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    # very light umlaut normalization
    s = s.replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    return s


def map_unit_name_to_id(unit_name: str, unit_mappings: dict) -> tuple[str | None, str | None]:
    if not unit_name:
        return None, None
    key = _normalize(unit_name)
    key = UNIT_SYNONYMS.get(key, unit_name if unit_name else None)
    if not key:
        return None, None
    # Try exact key match in mapping keys (case-insensitive)
    for name, meta in unit_mappings.items():
        if _normalize(name) == _normalize(key):
            return meta.get("new_id"), name
    # Try synonyms again against mapping keys
    for name, meta in unit_mappings.items():
        if _normalize(name) in UNIT_SYNONYMS and UNIT_SYNONYMS[_normalize(name)] == key:
            return meta.get("new_id"), name
    return None, key  # keep canonicalized name for display, even if id missing


def map_food_name_to_id(food_name: str, food_mappings: dict) -> tuple[str | None, str | None]:
    if not food_name:
        return None, None
    # Exact match by name (case-insensitive)
    norm_target = _normalize(food_name)
    for name, meta in food_mappings.items():
        if _normalize(name) == norm_target:
            return meta.get("new_id"), name
    # Loose startswith/contains fallback
    for name, meta in food_mappings.items():
        n = _normalize(name)
        if norm_target in n or n in norm_target:
            return meta.get("new_id"), name
    return None, food_name


def parse_original_text_with_openrouter(original_text: str) -> dict | None:
    if not OPENROUTER_HEADERS or not original_text:
        return None
    if original_text in PARSER_CACHE:
        return PARSER_CACHE[original_text]

    system = (
        "You are a strict ingredient parser for German cooking texts. "
        "Extract a single ingredient into JSON with keys: quantity (number or null), "
        "unit (string or null, singular German like 'Esslöffel','Teelöffel','Gramm','Milliliter','Liter','Prise','Stück','Zehe'), "
        "food (string, concise singular, capitalize where appropriate), note (string or null). "
        "Convert vulgar fractions to decimals (e.g., 1/2 -> 0.5). Do not guess amounts if missing. Output ONLY JSON."
    )
    user = f"Text: {original_text}"

    body = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                OPENROUTER_URL,
                headers=OPENROUTER_HEADERS,
                json=body,
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                parsed = json.loads(content)
                PARSER_CACHE[original_text] = parsed
                return parsed
            else:
                # Backoff on rate limits etc.
                if attempt < MAX_RETRIES:
                    time.sleep(attempt * 2)
                else:
                    return None
        except Exception:
            if attempt < MAX_RETRIES:
                time.sleep(attempt * 2)
            else:
                return None

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
        response = requests.get(url, headers=HEADERS, verify=MEALIE_VERIFY_SSL, timeout=REQUEST_TIMEOUT)
        
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

# --- Local deterministic parser (German) ---
FRACTION_MAP = {
    "½": 0.5, "1/2": 0.5, "¹/₂": 0.5,
    "¼": 0.25, "1/4": 0.25, "¾": 0.75, "3/4": 0.75,
    "⅓": 1/3, "1/3": 1/3, "⅔": 2/3, "2/3": 2/3,
}
UNIT_TOKEN_PATTERN = r"(?:" + "|".join(sorted({re.escape(k) for k in list(UNIT_SYNONYMS.keys()) + [
    "el","tl","g","kg","ml","l","esslöffel","teelöffel","gramm","milliliter","liter","prise","stück","zehe"
]})) + r")"

ADJECTIVE_NOTES = {
    "lauwarm": "lauwarm",
    "lauwarmes": "lauwarm",
    "getrocknet": "getrocknet",
    "getrocknete": "getrocknet",
    "ungesüßt": "ungesüßt",
    "ungesuszt": "ungesüßt",
}

# Singular overrides for display when quantity == 1
FOOD_SINGULAR_OVERRIDES = {
    "karotten": "Karotte",
    "zwiebeln": "Zwiebel",
    "tomaten": "Tomate",
    "gurken": "Gurke",
    "champignons": "Champignon",
    "kartoffeln": "Kartoffel",
    "bohnen": "Bohne",
    "erbsen": "Erbse",
    "datteln": "Dattel",
    "oliven": "Olive",
    "birnen": "Birne",
    "zitronen": "Zitrone",
    "limetten": "Limette",
}

def _to_number(tok: str) -> float | None:
    tok = tok.strip()
    if tok in FRACTION_MAP:
        return float(FRACTION_MAP[tok])
    # simple fraction a/b
    m = re.match(r"^(\d+)\s*/\s*(\d+)$", tok)
    if m:
        a, b = m.groups()
        try:
            return float(a) / float(b)
        except Exception:
            return None
    tok = tok.replace(",", ".")
    try:
        return float(tok)
    except Exception:
        return None


def parse_original_text_local(original_text: str) -> dict | None:
    if not original_text:
        return None
    text = original_text.strip()
    # extract parenthetical note
    paren_note = None
    m = re.search(r"\(([^\)]+)\)", text)
    if m:
        paren_note = m.group(1).strip()
        text = (text[:m.start()] + text[m.end():]).strip()

    # tokens
    tokens = text.split()
    qty = None
    unit = None
    note_parts = []

    # quantity first token (number or vulgar fraction)
    if tokens:
        q = _to_number(tokens[0])
        if q is not None:
            qty = q
            tokens = tokens[1:]

    # unit next token
    if tokens:
        t0 = _normalize(tokens[0])
        if t0 in UNIT_SYNONYMS:
            unit = UNIT_SYNONYMS[t0]
            tokens = tokens[1:]

    # Special-case: garlic cloves in various spellings (e.g., "2 knoblauchzehen" -> 2 Zehen Knoblauch)
    garlic_as_compound = False
    if unit is None and tokens:
        t0n = _normalize(tokens[0])
        t1n = _normalize(tokens[1]) if len(tokens) > 1 else ""
        if (
            t0n in {"knoblauchzehe", "knoblauchzehen", "koblauchzehe", "koblauchzehen"}
            or t0n.startswith("knoblauchzeh") or t0n.startswith("koblauchzeh")
            or (t0n == "knoblauch" and t1n in {"zehe", "zehen"})
            or (t0n == "koblauch" and t1n in {"zehe", "zehen"})
        ):
            unit = "Zehe"
            garlic_as_compound = True
            # consume one or two tokens depending on split variant
            if (t0n in {"knoblauch", "koblauch"} and t1n in {"zehe", "zehen"}):
                tokens = tokens[2:]
            else:
                tokens = tokens[1:]

    # remaining tokens: try to separate adjective notes from food
    # collect adjectives that match our list as notes, rest becomes food
    food_tokens = ["Knoblauch"] if garlic_as_compound else []
    for t in tokens:
        tn = _normalize(t)
        if tn in ADJECTIVE_NOTES:
            note_parts.append(ADJECTIVE_NOTES[tn])
        else:
            food_tokens.append(t)

    food = " ".join(food_tokens).strip()
    note = paren_note or (" ".join(note_parts).strip() if note_parts else None)

    # basic cleanup
    if food:
        # capitalize first word
        food = food[:1].upper() + food[1:]

    if qty is None and unit is None and not food:
        return None

    return {
        "quantity": qty,
        "unit": unit,
        "food": food if food else None,
        "note": note,
    }

# Helper: singularize food for display when quantity == 1
def _singularize_food_for_display(food: str, qty) -> str:
    if not food:
        return food
    try:
        qv = float(qty) if qty not in (None, "") else None
    except Exception:
        qv = None
    if qv is not None and abs(qv - 1.0) <= 1e-9:
        key = _normalize(food)
        if key in FOOD_SINGULAR_OVERRIDES:
            return FOOD_SINGULAR_OVERRIDES[key]
    return food

# Construct ingredients in the required format
def construct_ingredient_payload(old_ingr, unit_mappings, food_mappings):
    ingredients = []
    
    for ingr in old_ingr:
        # START: original mapping based on old ids (fallback)
        unit_entry = next((u for u in unit_mappings.values() if u.get("old_id") == ingr.get("unit_id")), {})
        food_entry = next((f for f in food_mappings.values() if f.get("old_id") == ingr.get("food_id")), {})

        unit_id = unit_entry.get("new_id")
        unit_name = next((name for name, u in unit_mappings.items() if u.get("old_id") == ingr.get("unit_id")), None)

        food_id = food_entry.get("new_id")
        food_name = next((name for name, f in food_mappings.items() if f.get("old_id") == ingr.get("food_id")), None)
        # END: fallback

        note = (ingr.get("note", "") or "").strip()
        quantity = ingr.get("quantity", 1.0)
        reference_id = ingr.get("reference_id", str(uuid.uuid4()))
        original_text = ingr.get("original_text", "")

        # --- Deterministic local parse first ---
        parsed = parse_original_text_local(original_text)
        # then LLM fallback only if needed
        if not parsed:
            parsed = parse_original_text_with_openrouter(original_text)

        parsed_food_for_display = None
        if parsed:
            q = parsed.get("quantity")
            u = parsed.get("unit")
            f = parsed.get("food")
            n = parsed.get("note")

            # Quantity: trust parsed; clear if not provided
            if q is not None:
                quantity = q
            else:
                quantity = None

            # Note
            if n:
                note = n.strip()

            if f:
                parsed_food_for_display = f.strip()

            # Unit: trust parsed; clear if not provided
            if u:
                u_id, u_name = map_unit_name_to_id(u, unit_mappings)
                unit_id = u_id if u_id else None
                unit_name = u_name if u_name else u  # keep parsed unit name for display if no id
            else:
                unit_id = None
                unit_name = None

            # Food mapping (fallback to existing if mapping not found)
            if f:
                f_id, f_name = map_food_name_to_id(f, food_mappings)
                food_id = f_id or food_id
                food_name = f_name or food_name

        # Enforce: unit "Zehe" only valid with garlic
        if unit_name and _normalize(unit_name) == "zehe":
            food_for_check = parsed_food_for_display or food_name or ""
            if "knoblauch" not in _normalize(food_for_check):
                unit_id = None
                unit_name = None

        # Construct display text (prefer parsed singular food name)
        display_parts = []
        if quantity not in (None, ""):
            display_parts.append(str(quantity))
        # Pluralize unit for display when appropriate (e.g., 2 Zehen, 2 Prisen)
        display_unit_name = unit_name
        try:
            qv = float(quantity) if quantity not in (None, "") else None
        except Exception:
            qv = None
        if display_unit_name and qv is not None and abs(qv - 1.0) > 1e-9:
            if display_unit_name == "Zehe":
                display_unit_name = "Zehen"
            elif display_unit_name == "Prise":
                display_unit_name = "Prisen"
        if display_unit_name:
            display_parts.append(display_unit_name)

        display_food = parsed_food_for_display or food_name
        if display_food:
            display_food = _singularize_food_for_display(display_food, quantity)
            display_parts.append(display_food)
        if note:
            display_parts.append(f"{note}")
        display = " ".join([p for p in display_parts if p]).strip()

        ingredient_payload = {
            "quantity": quantity if quantity not in (None, "") else None,
            "unit": {"id": unit_id, "name": unit_name} if unit_id and unit_name else None,
            "food": {"id": food_id, "name": food_name} if food_id and food_name else None,
            "note": note if note else None,
            "isFood": True,
            "disableAmount": False,
            "display": display if display else None,
            "referenceId": reference_id,
            "originalText": original_text if original_text else None,
        }

        ingredient_payload = {k: v for k, v in ingredient_payload.items() if v is not None}
        ingredients.append(ingredient_payload)

    return ingredients


# Send updated ingredients to Mealie
def update_recipe_ingredients(recipe_slug, ingredients, *, dry_run: bool = False):
    url = f"{MEALIE_URL}/api/recipes/{recipe_slug}"
    payload = {
        "recipeIngredient": ingredients,
        "settings": {
            "disableAmount": False  # Enable amounts at recipe level
        }
    }

    print(f"🔍 Sending updated ingredients for {recipe_slug}")

    if dry_run:
        print(f"🧪 Dry run: would PATCH {url} with {len(ingredients)} ingredients")
        return True
    
    # Retry logic for robust connection handling
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🔍 Attempt {attempt}/{MAX_RETRIES}: Updating ingredients for recipe {recipe_slug}")
            response = requests.patch(url, headers=HEADERS, json=payload, verify=MEALIE_VERIFY_SSL, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                print(f"✅ Successfully updated ingredients for recipe: {recipe_slug}")
                return True
            else:
                print(f"❌ Failed to update ingredients for recipe {recipe_slug} - {response.text}")
                return False
                
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
            print(f"⚠️ Connection issue on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                wait_time = attempt * 2  # Exponential backoff
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print(f"❌ Failed to update ingredients for recipe {recipe_slug} after {MAX_RETRIES} attempts")
                return False
        except Exception as e:
            print(f"❌ Unexpected error updating ingredients for recipe {recipe_slug}: {e}")
            return False

# Process recipes and update their ingredients
def process_recipe_updates(target_slugs: set[str] | None = None, *, dry_run: bool = False):
    print("🚀 Starting robust recipe ingredients update...")
    mappings = load_mappings()
    old_recipes, old_ingredients = load_old_database()
    new_recipes = fetch_all_recipes()

    if not new_recipes:
        print("⚠️ No recipes found. Exiting.")
        return

    # Optional filtering by slug for validation runs
    if target_slugs:
        before = len(new_recipes)
        new_recipes = {slug: r for slug, r in new_recipes.items() if slug in target_slugs}
        after = len(new_recipes)
        print(f"🎯 Filtering by slugs: matched {after}/{before}")
        if not new_recipes:
            print("⚠️ No recipes matched the provided slugs. Exiting.")
            return

    recipe_mappings = mappings.get("recipes", {})
    unit_mappings = mappings.get("units", {})
    food_mappings = mappings.get("foods", {})

    total_recipes = len(new_recipes)
    processed = 0
    successful = 0
    failed = 0

    print(f"📊 Found {total_recipes} recipes to process")

    for recipe_slug, recipe in new_recipes.items():
        processed += 1
        old_recipe_id = next((mapping["old_id"] for old_name, mapping in recipe_mappings.items() if mapping.get("new_id") == recipe["id"]), None)

        print(f"📋 Progress: {processed}/{total_recipes} - Processing: {recipe.get('name', recipe_slug)}")

        if old_recipe_id:
            old_ingr = [ingr for ingr in old_ingredients if str(ingr["recipe_id"]) == str(old_recipe_id)]
            if old_ingr:
                parsed_ingredients = construct_ingredient_payload(old_ingr, unit_mappings, food_mappings)
                if parsed_ingredients:
                    success = update_recipe_ingredients(recipe_slug, parsed_ingredients, dry_run=dry_run)
                    if success:
                        successful += 1
                    else:
                        failed += 1
                    time.sleep(1)  # Small delay between requests
                else:
                    print(f"⚠️ No valid ingredients constructed for recipe {recipe_slug}")
                    failed += 1
            else:
                print(f"⚠️ No old ingredients found for recipe {recipe_slug}")
                failed += 1
        else:
            print(f"⚠️ No old recipe ID mapping found for recipe {recipe_slug}")
            failed += 1

    print("\n🎉 Recipe ingredients update completed!")
    print(f"📊 Final Results:")
    print(f"✅ Successful updates: {successful}")
    print(f"❌ Failed updates: {failed}")
    print(f"📋 Total processed: {processed}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update Mealie recipe ingredients with optional LLM parsing.")
    parser.add_argument("--slugs", type=str, help="Comma-separated recipe slugs to process")
    parser.add_argument("--dry-run", action="store_true", help="Do not perform any API updates, just parse and report")
    args = parser.parse_args()

    target_slugs = None
    if args.slugs:
        target_slugs = set(s.strip() for s in args.slugs.split(",") if s.strip())
    elif os.getenv("TARGET_RECIPE_SLUGS"):
        target_slugs = set(s.strip() for s in os.getenv("TARGET_RECIPE_SLUGS").split(",") if s.strip())

    process_recipe_updates(target_slugs, dry_run=args.dry_run)
