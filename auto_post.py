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

# ------------------- FETCH TRENDING KEYWORDS -------------------
def fetch_trending_keywords():
    pytrends = TrendReq(hl='en-US', tz=360, retries=3, backoff_factor=0.1)
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

    return trending_keywords[:10] if trending_keywords else ["SEO strategies", "Google ranking tips"]

# ------------------- AI-BASED UNMINED KEYWORDS -------------------
def discover_unmined_keywords(topic):
    prompt = f"Generate 10 untapped, high-traffic, zero-competition keywords related to '{topic}'."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        return response["choices"][0]["message"]["content"].split("\n")
    except:
        return []

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

# --------------------- FETCH MULTIPLE IMAGES ---------------------
def fetch_images(topic, count=5):
    """Fetch multiple images from Unsplash based on the topic."""
    if not UNSPLASH_ACCESS_KEY:
        print("⚠️ Unsplash API Key Missing.")
        return []

    images = []
    url = f"https://api.unsplash.com/photos/random?query={topic}&count={count}&client_id={UNSPLASH_ACCESS_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            images = [img["urls"]["regular"] for img in data if "urls" in img]
    except:
        print(f"⚠️ Failed to fetch images.")
    
    return images

# --------------------- AI-GENERATED HASHTAGS ---------------------
def generate_hashtags(topic):
    prompt = f"Generate 5 relevant hashtags for a blog post on '{topic}'."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50
        )
        return response["choices"][0]["message"]["content"]
    except:
        return ""

# --------------------- AUTO POST TO WORDPRESS ---------------------
def post_to_wordpress(title, summary, content, topic):
    credentials = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    image_urls = fetch_images(topic, count=5)
    image_html = "".join([f'<img src="{url}" alt="{topic}" style="max-width:100%; height:auto;"/><br>' for url in image_urls])

    hashtags = generate_hashtags(topic)

    full_content = f"""
    <h2>Summary</h2>
    <p>{summary}</p><br>
    {image_html}
    <br>
    {content}
    <br>
    {hashtags}<br>
    """

    api_url = f"{WP_URL}/wp-json/wp/v2/posts"
    headers = {"Content-Type": "application/json"}
    post_data = {
        "title": title,
        "content": full_content,
        "status": "publish"
    }

    response = requests.post(api_url, json=post_data, headers=headers, auth=credentials)

    if response.status_code == 201:
        print(f"✅ Successfully posted: {title}")
        return True
    else:
        print(f"❌ Failed to post: {title}. HTTP {response.status_code}")
        return False

# --------------------- MAIN AUTO POST FUNCTION ---------------------
def auto_post():
    topic = random.choice(fetch_trending_keywords())
    unmined_keywords = discover_unmined_keywords(topic)
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
