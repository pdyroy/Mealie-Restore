# Where possible backup before trying ANY of this
**Scripts in this repo are MORE than capable of breaking your database**

# Mealie Restore 🥗

> Fork notice: This is a fork of https://github.com/Aesgarth/Mealie-Restore. All credit to the original authors; this fork adds uv-based workflow, safer defaults, retries/timeouts, and domain-specific ingredient parsing tweaks.

Mealie Restore is a collection of Python scripts for **restoring recipes, ingredients, categories, and other data** from a Mealie backup into a running Mealie instance.

## 📌 Features

- Upload recipes, ingredients, tools, categories, and tags to Mealie.
- Restore **recipe instructions** and **ingredients** with correct mappings.
- Update existing recipes with missing details (e.g., nutrition, users).
- Upload recipe images and associate them with correct recipes.
- Uses `mappings.json` to correctly map old IDs to new ones.
- Optional LLM-assisted ingredient parsing via OpenRouter.
- Safer defaults: SSL verification enabled by default, dry-run mode for updates.

## 🚀 Setup

### 1) Clone

```powershell
git clone https://github.com/Aesgarth/Mealie-Restore.git
cd Mealie-Restore
```

### 2) Install uv (Windows PowerShell)

```powershell
iwr https://astral.sh/uv/install.ps1 -UseBasicParsing | iex
# Restart the terminal if `uv` isn't found
uv --version
```

### 3) Install dependencies with uv

```powershell
uv sync
```

### 4) Configure environment

Create a `.env` file in the project root:

```
MEALIE_URL=https://your-mealie-instance
MEALIE_API_TOKEN=your-api-token
# Optional (default=true). Set to false to skip TLS verification for self-signed certs.
MEALIE_VERIFY_SSL=true

# Optional OpenRouter integration for ingredient parsing
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_MODEL=openai/gpt-oss-20b:free

# New defaults for fresh installs
DEFAULT_USER_PASSWORD=ChangeMe123!
DEFAULT_GROUP_ID=Home
DEFAULT_HOUSEHOLD=Family
```

Notes:
- Use only `MEALIE_API_TOKEN` for authentication.
- When `MEALIE_VERIFY_SSL=false`, TLS warnings are muted and requests use `verify=False`.

---

## 📦 Dependencies

- Managed via `pyproject.toml`. Use `uv sync` to create/update the local `.venv`.
- If you must use a requirements file, generate one separately and adjust the README accordingly.

Example run after syncing:

```powershell
uv run update_recipe_ingredients.py --dry-run
```

---

## ⚙️ Usage

1) Extract your backup ZIP so that `database.json` and the `data/recipes` folder exist in the repo root.

2) Restore order (run in this sequence):

   1. Categories
      ```powershell
      uv run upload_categories.py
      ```
   2. Ingredients
      ```powershell
      uv run upload_ingredients.py
      ```
   3. Tools
      ```powershell
      uv run upload_tools.py
      ```
   4. Tags
      ```powershell
      uv run upload_tags.py
      ```
   5. Recipes
      ```powershell
      uv run upload_recipes.py
      ```
   6. Generate ID mappings (required before images)
      ```powershell
      uv run data_update_map.py
      ```
   7. Upload images
      ```powershell
      uv run upload_recipe_images.py
      # or the robust version with retries
      uv run upload_recipe_images_robust.py
      ```
   8. Update details (instructions and ingredients)
      ```powershell
      uv run update_recipe_instructions.py
      # Safer run of ingredient updates (dry run first)
      uv run update_recipe_ingredients.py --dry-run
      # Then apply for real
      uv run update_recipe_ingredients.py
      ```

### Target a subset of recipes

```powershell
uv run update_recipe_ingredients.py --slugs vegane-manti-mit-sojafullung,veganer-zitronen-upside-down-kuchen --dry-run
```

---

## 🔐 Publishing & Safety

- Secrets are read from `.env` and never hard-coded.
- SSL verification is ON by default. Use `MEALIE_VERIFY_SSL=false` only for local/self-signed servers.
- Ingredient updates support `--dry-run` to preview payload construction without changing your Mealie data.
- Before publishing, ensure these are untracked/removed:
  - `.env`, `.env.*`
  - `database.json`, `database_backup_*.json`, `*.zip`
  - `data/` (including `data/recipes/` images)
  - `mappings.json`, `mappings_old.json`
  - Any local virtual envs: `.venv/`, `venv/`

---

## 🛠 Troubleshooting

- `database.json not found` → Extract your backup into the repo root.
- `mappings.json not found` → Run `uv run data_update_map.py` first.
- One recipe fails mapping (e.g., `test12`) → Add its mapping to `mappings.json` or exclude via `--slugs`.

---

## 🤝 Contributing

- Fork the repository and submit a Pull Request.
- Report issues in the **GitHub Issues** section.

---

## ⚠️ Disclaimer

This project is **not affiliated with Mealie**. Use at your own risk!

---

## 🐝 License

MIT License. See `LICENSE` for details.

