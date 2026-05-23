import os
import requests
import re
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY is not set.")
    exit(1)

def get_latest_models():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    res = requests.get(url)
    if res.status_code != 200:
        print("Failed to fetch models.")
        exit(1)
        
    models_data = res.json().get("models", [])
    
    flash_versions = []
    flash_lite_versions = []
    
    for m in models_data:
        name = m.get("name", "")
        # Look for models/gemini-X.Y-flash
        match_flash = re.match(r"models/gemini-(\d+\.\d+)-flash$", name)
        if match_flash:
            flash_versions.append((float(match_flash.group(1)), match_flash.group(0).replace("models/", "")))
            
        # Look for models/gemini-X.Y-flash-lite
        match_lite = re.match(r"models/gemini-(\d+\.\d+)-flash-lite$", name)
        if match_lite:
            flash_lite_versions.append((float(match_lite.group(1)), match_lite.group(0).replace("models/", "")))

    latest_flash = max(flash_versions, key=lambda x: x[0])[1] if flash_versions else "gemini-2.5-flash"
    latest_lite = max(flash_lite_versions, key=lambda x: x[0])[1] if flash_lite_versions else "gemini-3.1-flash-lite"
    
    return latest_flash, latest_lite

def update_config(filepath, latest_flash, latest_lite):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Replace MODEL_CHAT = "gemini-X.Y-flash"
        new_content = re.sub(r'MODEL_CHAT = "gemini-\d+\.\d+-flash"', f'MODEL_CHAT = "{latest_flash}"', content)
        # Replace MODEL_DASHBOARD = "gemini-X.Y-flash-lite"
        new_content = re.sub(r'MODEL_DASHBOARD = "gemini-\d+\.\d+-flash-lite"', f'MODEL_DASHBOARD = "{latest_lite}"', new_content)
        
        if new_content != content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated models in {filepath}")
            return True
        return False
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return False

if __name__ == "__main__":
    print("Checking for new Gemini models...")
    flash, lite = get_latest_models()
    print(f"Latest Flash: {flash} | Latest Lite: {lite}")
    
    changed = update_config("scripts/config.py", flash, lite)
    
    if changed:
        print("MODELS_UPDATED=true")
    else:
        print("Models are already up to date.")
