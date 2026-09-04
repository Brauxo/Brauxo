"""
Autonomous Gemini Model Scanner.
Discovers, validates, and updates the latest stable Gemini Flash model endpoint in config.py.
"""

from __future__ import annotations

import os
import re
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("[error] GEMINI_API_KEY is not set.")
    exit(1)


def test_model(session: requests.Session, model_name: str) -> bool:
    """Validate that a model candidate responds with HTTP 200."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": "ping"}]}]}
    try:
        res = session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
        return res.status_code == 200
    except Exception as err:
        print(f"[warning] Health-check for {model_name} failed: {err}")
        return False


def get_latest_working_model(session: requests.Session) -> str:
    """Fetch available models and return the latest verified operational flash model."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        res = session.get(url, timeout=10)
        if not res.ok:
            print("[warning] Failed to fetch remote models list, falling back to gemini-3.7-flash.")
            return "gemini-3.7-flash"

        models_data = res.json().get("models", [])
        candidates: list[tuple[float, str]] = []

        for m in models_data:
            name = m.get("name", "")
            match_flash = re.match(r"models/gemini-(\d+\.\d+)-flash$", name)
            if match_flash:
                version_num = float(match_flash.group(1))
                clean_name = match_flash.group(0).replace("models/", "")
                candidates.append((version_num, clean_name))

        candidates.sort(key=lambda x: x[0], reverse=True)

        for _, model_name in candidates:
            print(f"[info] Testing candidate {model_name}...")
            if test_model(session, model_name):
                print(f"[success] Model verified: {model_name}")
                return model_name
            print(f"[warning] Candidate {model_name} unavailable, testing next fallback...")

        return "gemini-3.7-flash"
    except Exception as err:
        print(f"[error] Model discovery failed: {err}")
        return "gemini-3.7-flash"


def update_config(filepath: str, latest_model: str) -> bool:
    """Update primary MODEL constant in config.py if changed."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        new_content = re.sub(r'MODEL\s*=\s*"[^"]+"', f'MODEL = "{latest_model}"', content)

        if new_content != content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"[success] Updated model in {filepath} -> {latest_model}")
            return True
        return False
    except FileNotFoundError:
        print(f"[error] Target config file not found: {filepath}")
        return False


def main() -> None:
    print("[start] Checking for latest operational Gemini models...")
    with requests.Session() as session:
        latest = get_latest_working_model(session)
        print(f"[info] Selected Model: {latest}")

        changed = update_config("scripts/config.py", latest)
        if changed:
            print("[success] MODELS_UPDATED=true")
        else:
            print("[info] Model is already up to date.")


if __name__ == "__main__":
    main()
