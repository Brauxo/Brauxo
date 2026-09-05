"""
Autonomous Daily Radar Engine.
Fetches ecosystem telemetry (HackerNews, GitHub activity, Open-Meteo weather),
and synthesizes an objective, high-signal systems engineering briefing with Gemini.
"""

from __future__ import annotations

import datetime
import os
import re
from dataclasses import dataclass
from typing import Optional

import requests
from dotenv import load_dotenv

from config import MODEL

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
USERNAME = "Brauxo"

if not GEMINI_API_KEY:
    print("[error] GEMINI_API_KEY is not set.")
    exit(1)

WMO_WEATHER_MAP: dict[int, tuple[str, str]] = {
    0: ("☀️", "Clear sky"),
    1: ("🌤️", "Mainly clear"),
    2: ("⛅", "Partly cloudy"),
    3: ("☁️", "Overcast"),
    45: ("🌫️", "Foggy"),
    48: ("🌫️", "Rime fog"),
    51: ("🌦️", "Light drizzle"),
    53: ("🌧️", "Moderate drizzle"),
    55: ("🌧️", "Dense drizzle"),
    61: ("🌦️", "Slight rain"),
    63: ("🌧️", "Moderate rain"),
    65: ("🌧️", "Heavy rain"),
    71: ("🌨️", "Light snow"),
    73: ("🌨️", "Moderate snow"),
    75: ("❄️", "Heavy snow"),
    80: ("🌦️", "Rain showers"),
    81: ("🌧️", "Heavy showers"),
    82: ("⛈️", "Violent showers"),
    95: ("⛈️", "Thunderstorm"),
}


@dataclass(frozen=True)
class WeatherTelemetry:
    temp: float
    feels_like: float
    temp_min: float
    temp_max: float
    humidity: int
    wind_speed: float
    condition: str
    icon: str

    def format_line(self) -> str:
        return (
            f"{self.icon} **{self.temp:.1f}°C** "
            f"({self.temp_min:.1f}°C / {self.temp_max:.1f}°C) · "
            f"{self.condition} · 💧 {self.humidity}% · 💨 {self.wind_speed:.0f} km/h"
        )


def get_weather(session: requests.Session) -> WeatherTelemetry:
    """Fetch current and daily weather metrics for Paris from Open-Meteo."""
    fallback = WeatherTelemetry(
        temp=19.0, feels_like=19.0, temp_min=15.0, temp_max=22.0,
        humidity=65, wind_speed=10.0, condition="Moderate", icon="⛅"
    )
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=48.8566&longitude=2.3522"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        "&timezone=Europe%2FParis"
    )
    try:
        resp = session.get(url, timeout=6)
        if not resp.ok:
            return fallback

        data = resp.json()
        current = data.get("current", {})
        daily = data.get("daily", {})

        wmo_code = current.get("weather_code", 0)
        icon, condition = WMO_WEATHER_MAP.get(wmo_code, ("⛅", "Clear"))

        return WeatherTelemetry(
            temp=current.get("temperature_2m", fallback.temp),
            feels_like=current.get("apparent_temperature", fallback.feels_like),
            temp_min=daily.get("temperature_2m_min", [fallback.temp_min])[0],
            temp_max=daily.get("temperature_2m_max", [fallback.temp_max])[0],
            humidity=current.get("relative_humidity_2m", fallback.humidity),
            wind_speed=current.get("wind_speed_10m", fallback.wind_speed),
            condition=condition,
            icon=icon,
        )
    except Exception as err:
        print(f"[warning] Open-Meteo fetch failed: {err}")
        return fallback


def get_hn_news(session: requests.Session, limit: int = 8) -> str:
    """Fetch top tech discussions from HackerNews."""
    try:
        resp = session.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=6)
        if not resp.ok:
            return "Frontier AI and distributed systems updates."

        story_ids = resp.json()[:limit]
        stories: list[str] = []
        for sid in story_ids:
            item_resp = session.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=4)
            if item_resp.ok:
                item = item_resp.json()
                if item and "title" in item:
                    stories.append(f"- {item['title']} ({item.get('url', 'https://news.ycombinator.com')})")

        return "\n".join(stories) if stories else "Frontier AI and distributed systems updates."
    except Exception as err:
        print(f"[warning] HackerNews fetch failed: {err}")
        return "Ecosystem discussions synchronized."


def get_github_activity(session: requests.Session) -> str:
    """Fetch recent public push events for the user."""
    if not GITHUB_TOKEN:
        return "Telemetry live"
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }
        resp = session.get(f"https://api.github.com/users/{USERNAME}/events/public", headers=headers, timeout=6)
        if resp.ok:
            events = resp.json()
            pushes = sum(1 for e in events if e.get("type") == "PushEvent")
            return f"{pushes} recent pushes detected"
        return "Active"
    except Exception as err:
        print(f"[warning] GitHub activity fetch failed: {err}")
        return "Active"


def call_gemini(session: requests.Session, prompt: str, model_name: str) -> Optional[str]:
    """Invoke Gemini generateContent endpoint with error handling."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        resp = session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        if resp.ok:
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        print(f"[warning] Model {model_name} returned status {resp.status_code}")
        return None
    except Exception as err:
        print(f"[error] Request to {model_name} failed: {err}")
        return None


def generate_briefing(session: requests.Session, news: str, weather: WeatherTelemetry, activity: str) -> str:
    """Generate the markdown dashboard section using Gemini with cascading fallback."""
    prompt = f"""
You are an autonomous AI curator embedded in an engineering GitHub profile focused on AI Systems, Distributed Data Platforms, and Cloud Infrastructure.

Context Feeds:
[HackerNews Top Tech Stories]:
{news}

Task:
Produce a 2-part engineering digest:
1. [ECOSYSTEM_PULSE]: 1 to 2 sentences summarizing the most significant engineering breakthrough, model release, or developer tool discussion from the feed.
2. [ARCHITECTURAL_INSIGHT]: 1 to 2 sentences analyzing the broader architectural impact (e.g. data platform scaling, latency, streaming pipelines, or compute efficiency).

Strict Rules:
- DO NOT mention any personal names.
- DO NOT write in first person ("I", "my").
- Maintain a senior, technical, objective engineering tone.
- Format exactly with these two section tags:
[ECOSYSTEM_PULSE]
<1-2 sentences>

[ARCHITECTURAL_INSIGHT]
<1-2 sentences>
"""
    print(f"[info] Synthesizing digest with {MODEL}...")
    ai_raw = call_gemini(session, prompt, MODEL)
    if ai_raw:
        print(f"[success] Response received from {MODEL}")
    else:
        print(f"[warning] {MODEL} did not return valid text, using baseline summary")

    pulse_text = "Vectorized query execution and specialized accelerator pipelines continue to redefine high-throughput data processing."
    insight_text = "Modern data architectures prioritize decoupling storage from compute to ensure cost efficiency and sub-second query performance at petabyte scale."

    if ai_raw:
        pulse_match = re.search(r"\[ECOSYSTEM_PULSE\]\s*(.*?)(?=\[ARCHITECTURAL_INSIGHT\]|$)", ai_raw, re.DOTALL)
        insight_match = re.search(r"\[ARCHITECTURAL_INSIGHT\]\s*(.*)", ai_raw, re.DOTALL)
        if pulse_match and pulse_match.group(1).strip():
            pulse_text = pulse_match.group(1).strip()
        if insight_match and insight_match.group(1).strip():
            insight_text = insight_match.group(1).strip()

    current_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    badge_date = current_date.replace("-", "--")

    match = re.search(r"gemini-(\d+(?:\.\d+)?)", MODEL)
    badge_version = match.group(1) if match else "Flash"

    return f"""
<div align="center">
  <img src="https://img.shields.io/badge/Agent-Autonomous-10b981?style=flat-square&logo=githubactions&logoColor=white" />
  <img src="https://img.shields.io/badge/Engine-Gemini%20{badge_version}-6366f1?style=flat-square&logo=google-gemini&logoColor=white" />
  <img src="https://img.shields.io/badge/Sync-{badge_date}-475569?style=flat-square&logo=git&logoColor=white" />
</div>

<br>

> 📍 **Paris**: {weather.format_line()} &nbsp;|&nbsp; ⚡ **GitHub**: {activity}  
>
> **Ecosystem Pulse**  
> {pulse_text}
>
> **Architectural Perspective**  
> {insight_text}
""".strip()


def update_readme(briefing: str, path: str = "README.md") -> None:
    """Inject updated briefing content into README markers."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r"<!--AI_DASHBOARD_START-->.*?<!--AI_DASHBOARD_END-->", re.DOTALL)
    new_content = f"<!--AI_DASHBOARD_START-->\n{briefing}\n<!--AI_DASHBOARD_END-->"

    with open(path, "w", encoding="utf-8") as f:
        f.write(pattern.sub(new_content, content))


def main() -> None:
    print("[start] Autonomous Daily Radar synchronization...")
    with requests.Session() as session:
        weather = get_weather(session)
        activity = get_github_activity(session)
        news = get_hn_news(session)

        print("[info] Synthesizing digest with Gemini...")
        briefing = generate_briefing(session, news, weather, activity)

        print("[info] Writing updates to README.md...")
        update_readme(briefing)
        print("[success] Synchronization completed.")


if __name__ == "__main__":
    main()
