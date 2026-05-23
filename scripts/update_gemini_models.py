import os
import requests
import re
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY is not set.")
    exit(1)

def get_latest_model():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    res = requests.get(url)
    if res.status_code != 200:
        print("Failed to fetch models.")
        exit(1)
        
    models_data = res.json().get("models", [])
    
    flash_versions = []
    
    for m in models_data:
        name = m.get("name", "")
        # Look for models/gemini-X.Y-flash
        match_flash = re.match(r"models/gemini-(\d+\.\d+)-flash$", name)
        if match_flash:
            flash_versions.append((float(match_flash.group(1)), match_flash.group(0).replace("models/", "")))

    latest_flash = max(flash_versions, key=lambda x: x[0])[1] if flash_versions else "gemini-2.5-flash"
    
    return latest_flash

def update_config(filepath, latest_model):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Replace MODEL = "gemini-X.Y-flash"
        new_content = re.sub(r'MODEL = "gemini-\d+\.\d+-flash"', f'MODEL = "{latest_model}"', content)
        
        if new_content != content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated model in {filepath}")
            return True
        return False
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return False

if __name__ == "__main__":
    print("Checking for new Gemini models...")
    latest = get_latest_model()
    print(f"Latest Model: {latest}")
    
    changed = update_config("scripts/config.py", latest)
    
    if changed:
        print("MODELS_UPDATED=true")
    else:
        print("Model is already up to date.")
