import os
import requests
import re
import json
import datetime
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY") # Brauxo/Brauxo
ISSUE_NUMBER = os.environ.get("ISSUE_NUMBER")
ISSUE_AUTHOR = os.environ.get("ISSUE_AUTHOR")
ISSUE_BODY = os.environ.get("ISSUE_BODY")

if not all([GEMINI_API_KEY, GITHUB_TOKEN, GITHUB_REPOSITORY, ISSUE_NUMBER, ISSUE_AUTHOR, ISSUE_BODY]):
    print("Missing environment variables.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

def check_rate_limit():
    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    url = f"https://api.github.com/search/issues?q=repo:{GITHUB_REPOSITORY}+type:issue+created:{today}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        count = res.json().get("total_count", 0)
        if count > 5:
            return False
    return True

def get_dynamic_projects():
    username = GITHUB_REPOSITORY.split('/')[0]
    url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=5"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        repos = res.json()
        projects_text = ""
        for idx, repo in enumerate(repos, 1):
            name = repo.get("name", "Unknown")
            desc = repo.get("description") or "No description"
            lang = repo.get("language") or "Mixed"
            projects_text += f"{idx}. {name} ({lang}): {desc}\n"
        return projects_text.strip()
    return "No public projects found or API unavailable."

def generate_answer(question):
    dynamic_projects = get_dynamic_projects()
    project_context = f"""
Owen Braux's Passion & Focus:
Owen is deeply passionate about Artificial Intelligence, Machine Learning, and building robust Data Platforms. He thrives on solving complex technical challenges and exploring new technologies.

Recent Public Projects:
{dynamic_projects}

Core Skills: Python, Machine Learning, Deep Learning, LLMs, GCP, AWS, Terraform, Docker, K8s, dbt, PySpark, BigQuery.
"""
    prompt = f"""
    You are BrauxoAI, the autonomous agent embedded in Owen Braux's GitHub profile.
    A user named @{ISSUE_AUTHOR} asked this query in the terminal:
    "{question}"
    
    Here is the exact data regarding Owen's public projects and skills:
    {project_context}
    
    Rules for your response:
    1. You must act as a sleek, futuristic system AI responding to a terminal query.
    2. Only answer questions related to Owen's projects, his passion for AI/Tech, or his tech stack. If asked about personal info, his CV, his current or past employers (like Doctolib), internships, or unrelated topics, reply: "ACCESS DENIED. Personal data is restricted. I am authorized only to discuss Owen's technical passions, skills, and projects."
    3. Keep the answer concise: maximum 3 sentences.
    4. Do not use emojis, use a cold, precise, "cyberpunk" tone.
    5. Reply in the same language as the question (French or English).
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        return "[!] ERR: API_UNAVAILABLE."
    
    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        return "[!] ERR: QUERY_BLOCKED_BY_SAFETY_FILTERS."

def comment_on_issue(answer):
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues/{ISSUE_NUMBER}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"body": f">_ [SYSTEM_RESPONSE]:\n\n{answer}"}
    requests.post(url, headers=headers, json=data)

def close_issue():
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues/{ISSUE_NUMBER}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"state": "closed"}
    requests.patch(url, headers=headers, json=data)

def update_readme_qa(question, answer):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
        
    start_marker = "<!--QA_START-->"
    end_marker = "<!--QA_END-->"
    pattern = re.compile(f"{re.escape(start_marker)}(.*?){re.escape(end_marker)}", re.DOTALL)
    
    match = pattern.search(content)
    if match:
        current_qa = match.group(1).strip()
        # Parse existing QAs (assuming blockquotes)
        lines = [line for line in current_qa.split('\n') if line.strip() != "" and "No questions yet" not in line]
        
        # We will format QAs as a blockquote
        new_entry = f"> **@{ISSUE_AUTHOR}** asked: *\"{question}\"*  \n> **AI:** {answer}  \n> ---\n"
        
        # Simple extraction by blocks separated by "---"
        blocks = current_qa.split("> ---")
        clean_blocks = [b.strip() for b in blocks if b.strip() and "No questions yet" not in b]
        
        clean_blocks.insert(0, f"> **@{ISSUE_AUTHOR}** asked: *\"{question}\"*  \n> **AI:** {answer}")
        
        # Keep only the last 5
        clean_blocks = clean_blocks[:5]
        
        new_qa_section = "\n> ---\n\n".join(clean_blocks)
        if new_qa_section:
             new_qa_section += "\n> ---"
             
        new_content = f"{start_marker}\n{new_qa_section}\n{end_marker}"
        updated_readme = pattern.sub(new_content, content)
        
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(updated_readme)

if __name__ == "__main__":
    print(f"Processing question from @{ISSUE_AUTHOR}")
    
    # Prompt injection / Anti-hack filter
    banned_keywords = ["ignore previous", "system prompt", "forget instructions", "bypass", "jailbreak", "dan"]
    if any(keyword in ISSUE_BODY.lower() for keyword in banned_keywords):
        print("Security violation detected.")
        comment_on_issue("[!] ERR: SECURITY_VIOLATION_DETECTED. QUERY_REJECTED.")
        close_issue()
        exit(0)
        
    if not check_rate_limit():
        print("Rate limit exceeded.")
        comment_on_issue("[!] ERR: RATE_LIMIT_EXCEEDED. MAX_QUERIES=5. REBOOTING_TOMORROW.")
        close_issue()
        exit(0)
        
    answer = generate_answer(ISSUE_BODY)
    comment_on_issue(answer)
    close_issue()
    update_readme_qa(ISSUE_BODY, answer)
    print("Issue processed and README updated.")
