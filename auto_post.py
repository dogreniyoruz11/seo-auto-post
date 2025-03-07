import os
import random
import requests
import openai
import json
import backoff
import time  # Import time for delay
import google.generativeai as genai
from pytrends.request import TrendReq
from requests.auth import HTTPBasicAuth
from PIL import Image
from io import BytesIO
from openai import OpenAIError  # ✅ Import the correct OpenAI error handler

# ----------------------- CONFIGURATION -----------------------
WP_URL = os.getenv("WP_URL")  # WordPress URL
WP_USERNAME = os.getenv("WP_USERNAME")  # WordPress Username
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")  # WordPress App Password

# ✅ Configure Google Gemini API Key
GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")

if GOOGLE_GEMINI_API_KEY:
    genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
else:
    raise ValueError("❌ GOOGLE_GEMINI_API_KEY is missing! Set it in Railway environment variables.")

# ✅ Configure OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # YouTube API Key
CANVA_API_KEY = os.getenv("CANVA_API_KEY")  # Canva API Key
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")  # Unsplash API Key
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")  # Pexels API Key
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")  # Pixabay API Key

# ✅ Remove Duplicate GOOGLE_GEMINI_API_KEY

# ------------------- AI CONTENT GENERATION -------------------
@backoff.on_exception(backoff.expo, OpenAIError, max_tries=5)
def generate_with_openai(prompt):
    """Generate AI response using OpenAI API."""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"].strip()

# ------------------- TRENDING KEYWORDS DISCOVERY -------------------
def fetch_trending_keywords():
    """Fetch trending keywords from Google Trends while handling empty responses safely."""
    pytrends = TrendReq()
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
            pytrends.build_payload(group, timeframe='now 7-d')
            time.sleep(2)  # Avoid Google Trends rate limits
            trends = pytrends.related_queries()

            if trends and isinstance(trends, dict):
                for kw in group:
                    if kw in trends and trends[kw] and 'top' in trends[kw] and trends[kw]['top'] is not None:
                        queries = trends[kw]['top']['query'].tolist()
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

    try:
        summary = generate_with_openai(summary_prompt)
        content = generate_with_openai(content_prompt)
        return summary, content

    except OpenAIError as e:
        print(f"⚠️ OpenAI Failed: {e}. Switching to Google Gemini AI.")

        try:
            model = genai.GenerativeModel("gemini-pro")
            summary_response = model.generate_content(summary_prompt)
            summary = summary_response.text.strip()

            content_response = model.generate_content(content_prompt)
            content = content_response.text.strip()

            return summary, content
        except Exception as gemini_error:
            print(f"❌ Google Gemini AI Failed: {gemini_error}")
            return None, None

# --------------------- IMAGE FETCH & COMPRESSION ---------------------
def fetch_image(topic):
    """Fetches an image from Unsplash API."""
    url = f"https://api.unsplash.com/photos/random?query={topic}&client_id={UNSPLASH_ACCESS_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["urls"]["regular"]
    else:
        print("⚠️ Failed to fetch image from Unsplash. Using fallback image.")
        return "https://example.com/sample.jpg"

def fetch_and_compress_image(topic):
    """Fetch and compress an image before uploading."""
    image_url = fetch_image(topic)
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    img = img.resize((800, int(img.height * (800 / img.width))))
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=75, optimize=True)
    return image_url  # Replace with actual upload function

# --------------------- AUTO POST TO WORDPRESS ---------------------
def post_to_wordpress(title, summary, content, topic):
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    image_url = fetch_and_compress_image(topic)

    full_content = f"""
    <h2>Summary</h2>
    <p>{summary}</p><br>
    <img src='{image_url}' alt='{title}' width='800' /><br>
    {content}<br>
    """

    post_data = {
        "title": title,
        "content": full_content,
        "status": "publish"
    }

    headers = {"Content-Type": "application/json"}
    
    response = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", json=post_data, headers=headers, auth=auth)

    if response.status_code == 201:
        print(f"✅ Successfully posted: {title}")
    else:
        print(f"❌ Failed to post: {title}")
        print(f"⚠️ HTTP Status Code: {response.status_code}")
        print(f"⚠️ Response Content: {response.text}")

# --------------------- MAIN AUTO POST FUNCTION ---------------------
def auto_post():
    for _ in range(5):
        topic = random.choice(fetch_trending_keywords())
        summary, content = generate_article(topic)
        if summary and content:
            post_to_wordpress(topic, summary, content, topic)
            print(f"✅ Posted article on: {topic}")
        time.sleep(300)  # Runs every 5 minutes

auto_post()
