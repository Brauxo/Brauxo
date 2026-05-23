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
        return "Could not retrieve the Picture of the Day. Please check back tomorrow."

    title = data.get("title", "No Title Available")
    explanation = data.get("explanation", "No explanation available.")
    media_type = data.get("media_type")

    if media_type == "image":
        image_url = data.get("hdurl") or data.get("url")
        if image_url:
            image_tag = f"![{title}]({image_url})"
        else:
            image_tag = "An image was expected, but the URL was missing."
    else:
        # handle other media types (like video)
        direct_url = data.get("url")
        
        if direct_url:
            # If a direct URL is provided
            image_tag = f"#### [Click here to view today's content]({direct_url})"
        else:
            # Build a link to page for that day
            apod_date = data.get("date", "") 
            if apod_date:
                date_parts = apod_date.split('-')
                formatted_date = f"{date_parts[0][2:]}{date_parts[1]}{date_parts[2]}"
                fallback_url = f"https://apod.nasa.gov/apod/ap{formatted_date}.html"
                image_tag = f"#### [Click here to see the content on the APOD website]({fallback_url})"
            else:
                image_tag = "Content is available, but the link could not be determined."

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