import os
import random
import requests
import openai
import json
import backoff
import time
import google.generativeai as genai
from pytrends.request import TrendReq
from requests.auth import HTTPBasicAuth
from PIL import Image
from io import BytesIO
from openai import OpenAIError

# ----------------------- CONFIGURATION -----------------------
WP_URL = os.getenv("WP_URL")  # WordPress URL
WP_USERNAME = os.getenv("WP_USERNAME")  # WordPress Username
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")  # WordPress App Password

# ✅ Configure Google Gemini API Key
GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
if GOOGLE_GEMINI_API_KEY:
    genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
else:
    print("❌ WARNING: GOOGLE_GEMINI_API_KEY is missing! Set it in Railway environment variables.")

# ✅ Configure OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("❌ ERROR: OPENAI_API_KEY is missing! Set it in Railway environment variables.")
else:
    openai.api_key = OPENAI_API_KEY

# ✅ Configure Image APIs
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")


# ------------------- AI CONTENT GENERATION -------------------
@backoff.on_exception(backoff.expo, OpenAIError, max_tries=5)
def generate_with_openai(prompt):
    """Generate AI response using OpenAI API with retry mechanism."""
    try:
        response = openai.ChatCompletion.create(  # ✅ Correct OpenAI call
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"❌ OpenAI API Error: {e}")
        return None



# ------------------- FIXED: TRENDING KEYWORDS DISCOVERY -------------------

def fetch_trending_keywords():
    """Fetch trending keywords from Google Trends while handling empty responses safely."""
    pytrends = TrendReq(hl='en-US', tz=360, retries=3, backoff_factor=0.1)  # ✅ Added retries and backoff
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
            pytrends.build_payload(group, timeframe='now 7-d', geo='US')  # ✅ Added geo='US'
            time.sleep(2)  # Avoid Google Trends rate limits
            trends = pytrends.related_queries()

            if trends:
                for kw in group:
                    if trends.get(kw) and isinstance(trends[kw], dict):
                        top_queries = trends[kw].get('top')
                        if isinstance(top_queries, dict) and 'query' in top_queries:
                            queries = top_queries['query'].tolist()
                            trending_keywords.extend(queries)
        except Exception as e:
            print(f"⚠️ Google Trends API Error for {group}: {e}")

    if not trending_keywords:
        print("❌ No trending keywords found. Using fallback default keywords.")
        trending_keywords = [
            "SEO strategies", "Google ranking tips", "YouTube video SEO",
            "AI marketing automation", "content marketing growth", "best affiliate marketing methods"
        ]

    return trending_keywords[:10]  # Return top 10 results


# ------------------- AI ARTICLE GENERATION -------------------
def generate_article(topic):
    """Generate an AI-powered article using OpenAI & Google Gemini AI."""
    summary_prompt = f"Generate a 3-4 sentence summary of an article about '{topic}'."
    content_prompt = f"Write a 1500-2000 word engaging SEO-optimized article on '{topic}'. Include a Table of Contents."

    summary = generate_with_openai(summary_prompt)
    content = generate_with_openai(content_prompt)

    if summary and content:
        return summary, content

    print("⚠️ OpenAI Failed. Switching to Google Gemini AI.")
    try:
        model_name = "gemini-1.5-pro-latest"
        model = genai.GenerativeModel(model_name)

        summary_response = model.generate_content(summary_prompt)
        content_response = model.generate_content(content_prompt)

        return summary_response.text.strip(), content_response.text.strip()
    except Exception as gemini_error:
        print(f"❌ Google Gemini AI Failed: {gemini_error}")
        return None, None


# --------------------- IMAGE FETCH & COMPRESSION ---------------------
def fetch_image(topic):
    """Fetches an image from Unsplash API."""
    if not UNSPLASH_ACCESS_KEY:
        print("⚠️ Unsplash API Key Missing. Skipping image fetch.")
        return None

    url = f"https://api.unsplash.com/photos/random?query={topic}&client_id={UNSPLASH_ACCESS_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data["urls"]["regular"]
    except Exception as e:
        print(f"⚠️ Failed to fetch image from Unsplash: {e}")
    return None


# --------------------- AUTO POST TO WORDPRESS ---------------------
def post_to_wordpress(title, summary, content):
    """Posts an article to WordPress using REST API."""

    # ✅ Check if WP_URL is valid
    if not WP_URL or not WP_URL.startswith("http"):
        print("❌ ERROR: WP_URL is missing or invalid! Check your Railway environment variables.")
        return False

    # ✅ Correct API Endpoint
    api_url = f"{WP_URL}/wp-json/wp/v2/posts"

    # ✅ Set up authentication and headers
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    headers = {"Content-Type": "application/json"}

    # ✅ Prepare post data
    post_data = {
        "title": title,
        "content": f"<h2>Summary</h2><p>{summary}</p><br>{content}<br>",
        "status": "publish"
    }

    # ✅ Send the POST request
    response = requests.post(api_url, json=post_data, headers=headers, auth=auth)

    # ✅ Debugging Output
    print(f"🔄 Posting to: {api_url}")
    print(f"📡 Request Headers: {headers}")
    print(f"📄 Request Body: {post_data}")

    # ✅ Handle Response
    if response.status_code == 201:
        print(f"✅ Successfully posted: {title}")
        return True
    else:
        print(f"❌ Failed to post: {title}. HTTP {response.status_code}. Response: {response.text}")
        return False
# --------------------- MAIN AUTO POST FUNCTION ---------------------
def auto_post():
    for _ in range(5):
        topic = random.choice(fetch_trending_keywords())
        summary, content = generate_article(topic)
        if summary and content:
            post_to_wordpress(topic, summary, content, topic)
        else:
            print(f"❌ Failed to generate article for: {topic}")
        time.sleep(300)

auto_post()
