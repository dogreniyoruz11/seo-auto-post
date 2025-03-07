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
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# ✅ Configure APIs
openai.api_key = OPENAI_API_KEY
if GOOGLE_GEMINI_API_KEY:
    genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
else:
    print("❌ WARNING: GOOGLE_GEMINI_API_KEY is missing!")

# -------------------- GENERATE AI SUMMARY --------------------
def generate_ai_summary(content):
    summary_prompt = f"Summarize the following blog content in 3-4 concise sentences:\n{content}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=100
        )
        return response["choices"][0]["message"]["content"]
    except:
        return "Summary not available."

# -------------------- FORMAT ARTICLE CONTENT --------------------
def format_article(title, summary, content, video_embed, hashtags, images):
    ai_summary = generate_ai_summary(content)
    formatted_content = f"""
    <h1>{title}</h1>
    <h2>Summary</h2>
    <p><strong>{ai_summary}</strong></p>
    {''.join([f'<img src="{img}" alt="{title}" style="max-width:100%; height:auto;"/><br>' for img in images])}
    <h2>Table of Contents</h2>
    <ul>
        <li><a href="#introduction">Introduction</a></li>
        <li><a href="#main-content">Main Content</a></li>
        <li><a href="#conclusion">Conclusion</a></li>
    </ul>
    <h2 id="introduction">Introduction</h2>
    <p>{content[:300]}</p>
    <h2 id="main-content">Main Content</h2>
    <p>{content[300:]}</p>
    <h2 id="conclusion">Conclusion</h2>
    <p>In conclusion, this article covered {title} and provided key insights...</p>
    <h2>Watch Related Video</h2>
    {video_embed}
    <h2>Popular Hashtags</h2>
    <p>{hashtags}</p>
    <h2>Share This Post</h2>
    <a href="https://www.facebook.com/sharer/sharer.php?u={WP_URL}">Share on Facebook</a> | 
    <a href="https://twitter.com/intent/tweet?url={WP_URL}&text={title}">Share on Twitter</a> | 
    <a href="https://www.linkedin.com/sharing/share-offsite/?url={WP_URL}">Share on LinkedIn</a>
    """
    return formatted_content

# --------------------- AUTO POST TO WORDPRESS ---------------------
def post_to_wordpress(title, summary, content, topic):
    credentials = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    video_embed = fetch_youtube_video(topic)
    images = fetch_images(topic, count=5)
    hashtags = generate_hashtags(topic)
    formatted_content = format_article(title, summary, content, video_embed, hashtags, images)
    api_url = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/posts"
    headers = {"Content-Type": "application/json"}
    post_data = {"title": title, "content": formatted_content, "status": "publish"}
    
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
