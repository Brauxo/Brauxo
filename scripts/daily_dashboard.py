import os
import requests
import datetime
import re
import json
from dotenv import load_dotenv
from config import MODEL_DASHBOARD

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
USERNAME = "Brauxo"

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY is not set.")
    exit(1)

def get_hn_news():
    try:
        top_stories = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()
        stories = []
        for story_id in top_stories[:8]:
            story = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json()
            if story and story.get('title'):
                stories.append(f"- {story.get('title')} ({story.get('url', '')})")
        return "\n".join(stories)
    except Exception:
        return "HN_API_OFFLINE"

def get_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=48.8566&longitude=2.3522&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=Europe%2FParis"
        res = requests.get(url).json()
        daily = res["daily"]
        t_max = daily["temperature_2m_max"][0]
        t_min = daily["temperature_2m_min"][0]
        code = daily["weathercode"][0]
        
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle", 
            55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 95: "Thunderstorm"
        }
        desc = weather_codes.get(code, "Unknown conditions")
        return f"{t_min}°C to {t_max}°C, {desc}"
    except Exception:
        return "METEO_API_OFFLINE"

def get_github_activity():
    if not GITHUB_TOKEN:
        return "SYNC_OFFLINE (Token Unlinked)"
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        events = requests.get(f"https://api.github.com/users/{USERNAME}/events/public", headers=headers).json()
        pushes = len([e for e in events if e.get('type') == 'PushEvent'])
        return f"{pushes} recent pushes detected"
    except Exception:
        return "GITHUB_API_OFFLINE"

def generate_briefing(news, weather, activity):
    prompt = f"""
    You are BrauxoAI, the core OS of Owen Braux's profile.
    
    [API_FEED_1: OPEN-METEO] Paris: {weather}
    [API_FEED_2: GITHUB_EVENTS] {activity}
    [API_FEED_3: HACKER_NEWS]
    {news}
    
    Context: Owen is deeply passionate about Artificial Intelligence, Machine Learning, and building scalable Data Platforms. He builds robust systems using Python, GCP, AWS, Terraform, K8s, PySpark, and dbt. His projects include a Bitcoin Analytics pipeline, an XGBoost Kaggle model, and a CNN for vision. DO NOT mention his current or past employers, internships, or any personal details outside of his technical passions.
    
    Task: Write a highly stylized, 3-section markdown briefing.
    Format exactly like this (replace bracketed text):
    
    **>_ [GLOBAL_SCAN]**
    > [1 sentence summarizing the most interesting AI/Data news from the HackerNews feed]
    
    **>_ [LOCAL_SYNERGY]**
    > [1-2 sentences relating the news or telemetry to Owen's passion for AI or his cloud skills in a cold, precise cyberpunk tone]

    **>_ [ENV_ANALYSIS]**
    > [1 sentence analyzing the Paris weather forecast and making a clever, Cyberpunk/Tech analogy (e.g., "Optimal GPU cooling conditions", "High thermal readings require underclocking", or "Clear skies optimize satellite telemetry").]
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_DASHBOARD}:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code != 200:
        ai_text = f"> ERROR: Gemini Core Unreachable. {res.text}"
    else:
        ai_text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    
    current_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    
    # Extract version from model string for the badge (e.g. gemini-3.1-flash-lite -> 3.1)
    try:
        badge_version = re.search(r"gemini-(\d+\.\d+)", MODEL_DASHBOARD).group(1)
    except Exception:
        badge_version = "X.X"
        
    dashboard_ui = f"""
<div align="center">
  <img src="https://img.shields.io/badge/STATUS-ONLINE-00ff00?style=for-the-badge&logo=matrix&logoColor=00ff00&color=black" />
  <img src="https://img.shields.io/badge/AGENT-GEMINI_{badge_version}-8A2BE2?style=for-the-badge&logo=google-gemini&logoColor=8A2BE2&color=black" />
</div>

<br>

```text
>_ RUNNING SYSTEM DIAGNOSTICS...
[+] SYS     :: Core Date      :: {current_date}
[+] ENV     :: Open-Meteo API :: {weather}
[+] DEV     :: GitHub REST    :: {activity}
[+] FEED    :: HackerNews API :: Sync Complete
```

<br>

### [ INTELLIGENCE_BRIEFING ]
{ai_text}
"""
    return dashboard_ui.strip()

def update_readme(briefing):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    pattern = re.compile(r"<!--AI_DASHBOARD_START-->.*?<!--AI_DASHBOARD_END-->", re.DOTALL)
    new_content = f"<!--AI_DASHBOARD_START-->\n{briefing}\n<!--AI_DASHBOARD_END-->"
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(pattern.sub(new_content, content))

if __name__ == "__main__":
    print("Fetching APIs...")
    news = get_hn_news()
    weather = get_weather()
    activity = get_github_activity()
    print("Calling Gemini...")
    briefing = generate_briefing(news, weather, activity)
    print("Updating README...")
    update_readme(briefing)
    print("Done!")
