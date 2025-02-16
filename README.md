# Where possible backup before trying ANY of this
**Scripts in this repo are MORE than capable of breaking your database**

# Mealie Restore 🥗

Mealie Restore is a collection of Python scripts for **restoring recipes, ingredients, categories, and other data** from a Mealie backup into a running Mealie instance.

## 📌 Features

- Upload recipes, ingredients, tools, categories, and tags to Mealie.
- Restore **recipe instructions** and **ingredients** with correct mappings.
- Update existing recipes with missing details (e.g., nutrition, users).
- Upload recipe images and associate them with correct recipes.
- Uses **mappings.json** to correctly map old IDs to new ones.

## 🚀 Installation

### 1️⃣ **Clone the Repository**

```sh
[git clone https://github.com/Aesgarth/Mealie-Restore.git]
cd mealie-restore
```

### 2️⃣ **Create a Virtual Environment (Optional)**

```sh
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

### 3️⃣ **Install Dependencies**

```sh
pip install -r requirements.txt
```

### 4️⃣ **Set Up API Configuration**

- Create a `.env` file in the root folder with:
  ```
  MEALIE_URL=https://your-mealie-instance.com
  API_TOKEN=your-secret-token
  ```
- Or modify `config.py` manually with your Mealie instance details.

---

## ⚙️ **Usage**

### **Step 1: Extract Your Backup**

Extract the **entire backup zip file** into the project directory. Ensure that `database.json` and all necessary files are available in the root directory.



### **Step 2: Run All Upload Scripts**

Run the scripts **in order**:

1. **Upload Categories**

   ```sh
   python upload_categories.py
   ```

2. **Upload Ingredients**

   ```sh
   python upload_ingredients.py
   ```

3. **Upload Tools**

   ```sh
   python upload_tools.py
   ```

4. **Upload Tags**

   ```sh
   python upload_tags.py
   ```

5. **Upload Recipes**

   ```sh
   python upload_recipes.py
   ```

6. **Upload Recipe Images**

   ```sh
   python upload_recipe_images.py
   ```

7. **Generate ID Mappings**

   ```sh
   python data_update_map.py
   ```

   - This script **fetches existing recipes** from Mealie and maps old recipe IDs to new ones.

8. **Run All Update Scripts**

   Run all scripts starting with `update_` in any order:

   ```sh
   python update_recipe_instructions.py
   python update_recipe_ingredients.py
   python update_recipes.py
   ```

   - This script **fetches existing recipes** from Mealie and maps old recipe IDs to new ones.

---

## 🛠 **Troubleshooting**

- **Issue: \*\*\*\*****`database.json not found!`**\
  ➔ Ensure your backup file is placed in the same folder as the scripts.

- **Issue: \*\*\*\*****`mappings.json not found!`**\
  ➔ Run `python data_update_map.py` first to create it.

- **Issue: \*\*\*\*****`Permission denied (Windows)`**\
  ➔ Close VS Code or other programs locking the files and try again.

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

