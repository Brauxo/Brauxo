import requests
import re
import os

# Markers for the readme
START_MARKER = "<!--NASA_PICTURE_START-->"
END_MARKER = "<!--NASA_PICTURE_END-->"

def fetch_nasa():
    api_key = os.environ.get("NASA_API_KEY")
    url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # raise
        data = response.json()
        return data
    except requests.exceptions.RequestException :
        return None

def format_readme(data):
    if not data:
        return "API is down and Could not retrieve the Picture of the Day. Contact me if you see this message."

    title = data.get("title", "No Title Available")
    explanation = data.get("explanation", "No explanation available.")
    
    # IF video
    if data.get("media_type") == "image":
        image_url = data.get("hdurl") or data.get("url")
        image_tag = f"![{title}]({image_url})"
    else:
        # Link if video
        video_url = data.get("url")
        image_tag = f"[Click here to watch the video of the day]({video_url})"

    # cleanup
    explanation_oneline = ' '.join(explanation.splitlines())
    
    return (
        f"#### {title}\n"
        f"{image_tag}\n"
        f"> {explanation_oneline}"
    )

def update_readme(new_content):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    pattern = re.compile(f"{re.escape(START_MARKER)}(.*?){re.escape(END_MARKER)}", re.DOTALL)
    new_readme = pattern.sub(f"{START_MARKER}\n{new_content}\n{END_MARKER}", content)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_readme)

if __name__ == "__main__":
    apod_data = fetch_nasa()
    markdown = format_readme(apod_data)
    update_readme(markdown)
    print("README updated")