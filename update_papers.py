import feedparser
import re
from datetime import datetime

# url from arvix
ARXIV_URL = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CV&sortBy=lastUpdatedDate&sortOrder=descending&max_results=5"
# MARKERS 
START_MARKER = "<!--PAPERS_START-->"
END_MARKER = "<!--PAPERS_END-->"

def format_date(parsed_date):
    return datetime(*parsed_date[:6]).strftime("%B %d, %Y")

def fetch_and_format_papers():
    feed = feedparser.parse(ARXIV_URL)
    markdown_list = []
    
    for entry in feed.entries:
        title = entry.title.replace('\n', ' ').strip()
        url = entry.link
        published_date = format_date(entry.published_parsed)

        markdown_list.append(
            f"* [{title}]({url}) - _Published on {published_date}_"
        )
        
    return "\n".join(markdown_list)

def update_readme(new_content):
    with open("README.md", "r") as readme_file:
        content = readme_file.read()

    pattern = re.compile(f"{re.escape(START_MARKER)}(.*?){re.escape(END_MARKER)}", re.DOTALL)
    new_readme_content = pattern.sub(f"{START_MARKER}\n{new_content}\n{END_MARKER}", content)

    with open("README.md", "w") as readme_file:
        readme_file.write(new_readme_content)

if __name__ == "__main__":
    papers_markdown = fetch_and_format_papers()
    update_readme(papers_markdown)
    print("README.md update sucess!")