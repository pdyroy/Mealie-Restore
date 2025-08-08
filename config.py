import os
from dotenv import load_dotenv

load_dotenv()

# --- Mealie Configuration ---
MEALIE_URL = os.getenv("MEALIE_URL", "http://localhost:9000")
MEALIE_API_TOKEN = os.getenv("MEALIE_API_TOKEN")
MEALIE_VERIFY_SSL = os.getenv("MEALIE_VERIFY_SSL", "true").strip().lower() in ("1", "true", "yes", "y")

HEADERS = {
    "Content-Type": "application/json",
}
if MEALIE_API_TOKEN:
    HEADERS["Authorization"] = f"Bearer {MEALIE_API_TOKEN}"

# --- OpenRouter Configuration (optional) ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Optional but recommended metadata for OpenRouter
OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "https://github.com/Aesgarth/Mealie-Restore")
OPENROUTER_X_TITLE = os.getenv("OPENROUTER_X_TITLE", "Mealie Restore")

def get_openrouter_headers():
    if not OPENROUTER_API_KEY:
        return None
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    if OPENROUTER_HTTP_REFERER:
        headers["HTTP-Referer"] = OPENROUTER_HTTP_REFERER
    if OPENROUTER_X_TITLE:
        headers["X-Title"] = OPENROUTER_X_TITLE
    return headers
