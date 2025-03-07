import os
import random
import requests
import openai
import google.generativeai as genai
from pytrends.request import TrendReq
from PIL import Image
from io import BytesIO
import schedule
import time
from requests.auth import HTTPBasicAuth
from requests.adapters import Retry  

# ----------------------- CONFIGURATION -----------------------
WP_URL = os.getenv("WP_URL")  # WordPress URL
WP_USERNAME = os.getenv("WP_USERNAME")  # WordPress Username
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")  # WordPress App Password

# ✅ API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

# ✅ Configure APIs
openai.api_key = OPENAI_API_KEY
if GOOGLE_GEMINI_API_KEY:
    genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
else:
    print("❌ WARNING: GOOGLE_GEMINI_API_KEY is missing!")

# ------------------- FETCH SEO-OPTIMIZED KEYWORDS -------------------
def fetch_trending_keywords():
    pytrends = TrendReq(hl='en-US', tz=360, retries=Retry(total=3, backoff_factor=0.1, allowed_methods=None))
    keyword_groups = [
        ["SEO", "keyword research", "Google SEO", "ranking on Google"],
        ["YouTube SEO", "rank YouTube videos", "YouTube algorithm", "video SEO"],
        ["digital marketing", "social media marketing", "content marketing", "online marketing"],
        ["AI marketing", "automation marketing", "AI tools"],
        ["SEO tools", "online marketing tools reviews"],
        ["content marketing tips", "blogging tips"],
        ["eCommerce marketing", "affiliate marketing strategies"]
    ]
    
    trending_keywords = []
    for group in keyword_groups:
        try:
            pytrends.build_payload(group, timeframe='now 7-d', geo='US')
            time.sleep(2)
            trends = pytrends.related_queries()
            if trends:
                for kw in group:
                    if trends.get(kw) and isinstance(trends[kw], dict):
                        top_queries = trends[kw].get('top')
                        if isinstance(top_queries, dict) and 'query' in top_queries:
                            queries = top_queries['query'].tolist()
                            trending_keywords.extend(queries)
        except Exception as e:
            print(f"⚠️ Google Trends API Error: {e}")
    
    return trending_keywords[:10] if trending_keywords else generate_unmined_keywords()

# ------------------- AI-BASED UNMINED KEYWORDS -------------------
def generate_unmined_keywords():
    prompt = "Generate 10 untapped, high-traffic, zero-competition SEO-related keywords."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        return response["choices"][0]["message"]["content"].split("\n")
    except:
        return ["SEO growth hacks", "hidden SEO tricks", "Google ranking loopholes"]

# -------------------- AI ARTICLE GENERATION --------------------
def generate_article(topic):
    summary_prompt = f"Generate a 3-4 sentence summary of an article about '{topic}'."
    content_prompt = f"Write a 1500-2000 word engaging SEO-optimized article on '{topic}'. Include a Table of Contents."
    
    try:
        summary = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=100
        )["choices"][0]["message"]["content"]

        content = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": content_prompt}],
            max_tokens=3000
        )["choices"][0]["message"]["content"]

        return summary, content
    except:
        print("⚠️ OpenAI Failed. Switching to Google Gemini AI.")
        try:
            model = genai.GenerativeModel("gemini-1.5-pro-latest")
            summary_response = model.generate_content(summary_prompt)
            content_response = model.generate_content(content_prompt)
            return summary_response.text.strip(), content_response.text.strip()
        except:
            print("❌ AI Failed: Skipping article generation.")
            return None, None

# --------------------- AUTO POST TO WORDPRESS ---------------------
def post_to_wordpress(title, summary, content, topic):
    credentials = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    api_url = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/posts"
    headers = {"Content-Type": "application/json"}
    post_data = {"title": title, "content": f"<h2>Summary</h2><p>{summary}</p><br>{content}", "status": "publish"}
    
    response = requests.post(api_url, json=post_data, headers=headers, auth=credentials)
    if response.status_code == 201:
        print(f"✅ Successfully posted: {title}")
    else:
        print(f"❌ Failed to post: {title}. HTTP {response.status_code}")

# --------------------- MAIN AUTO POST FUNCTION ---------------------
def auto_post():
    topic = random.choice(fetch_trending_keywords())
    summary, content = generate_article(topic)
    if summary and content:
        post_to_wordpress(topic, summary, content, topic)
    else:
        print(f"❌ Failed to generate article for: {topic}")

# --------------------- SCHEDULED POSTING ---------------------
schedule.every(2).minutes.do(auto_post)

while True:
    schedule.run_pending()
    time.sleep(60)
