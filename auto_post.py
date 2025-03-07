import os
import random
import requests
import openai
import json
import time  # Import time for delay
from pytrends.request import TrendReq
from PIL import Image
from io import BytesIO

# ----------------------- CONFIGURATION -----------------------
WP_URL = os.getenv("WP_URL")  # WordPress URL
WP_USERNAME = os.getenv("WP_USERNAME")  # WordPress Username
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")  # WordPress App Password

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # OpenAI API Key
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # YouTube API Key
CANVA_API_KEY = os.getenv("CANVA_API_KEY")  # Canva API Key
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")  # Unsplash API Key
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")  # Pexels API Key
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")  # Pixabay API Key
openai.api_key = OPENAI_API_KEY


# ------------------- TRENDING KEYWORDS DISCOVERY -------------------
def fetch_trending_keywords():
    """Fetch trending keywords from Google Trends while handling empty responses."""
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

            if trends:
                for kw in group:
                    if trends.get(kw) and trends[kw]['top'] is not None:
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


# ------------------- AI-BASED HIDDEN KEYWORDS -------------------
def discover_unmined_keywords(topic):
    """Finds hidden, high-traffic, zero-competition keywords using AI."""
    prompt = f"Generate 10 untapped, high-traffic, zero-competition keywords related to '{topic}'."
    client = openai.OpenAI()

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are an expert in keyword research."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content.split("\n")


# -------------------- AI ARTICLE GENERATION --------------------
def generate_article(topic):
    client = openai.OpenAI()

    summary_prompt = f"Generate a 3-4 sentence summary of an article about '{topic}'."
    summary_response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": summary_prompt}]
    )
    summary = summary_response.choices[0].message.content

    content_prompt = f"Write a 1500-2000 word engaging SEO-optimized article on '{topic}'. Include a Table of Contents."
    content_response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": content_prompt}]
    )
    content = content_response.choices[0].message.content

    return summary, content


# --------------------- IMAGE FETCH & COMPRESSION ---------------------
def fetch_image(topic):
    """Fetches an image from Unsplash, Pexels, or Pixabay."""
    return "https://example.com/sample.jpg"  # Replace with actual API call


def fetch_and_compress_image(topic):
    """Fetch and compress an image before uploading."""
    image_url = fetch_image(topic)
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    img = img.resize((800, int(img.height * (800 / img.width))))  # Keep aspect ratio
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=75, optimize=True)
    return image_url  # Replace with actual upload function


# --------------------- AI-GENERATED HASHTAGS ---------------------
def generate_hashtags(topic):
    client = openai.OpenAI()
    prompt = f"Generate 5 relevant hashtags for a blog post on '{topic}'."
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


# --------------------- AUTO POST TO WORDPRESS ---------------------

def post_to_wordpress(title, summary, content, topic):
    credentials = requests.auth._basic_auth_str(WP_USERNAME, WP_APP_PASSWORD)
    image_url = fetch_and_compress_image(topic)
    hashtags = generate_hashtags(topic)

    social_share_buttons = f"""
    <h3>📢 Share This Article</h3>
    <div class='social-share'>
        <a href='https://www.facebook.com/sharer/sharer.php?u=POST_URL' target='_blank'>Facebook</a> |
        <a href='https://twitter.com/intent/tweet?text={title}&url=POST_URL' target='_blank'>Twitter</a> |
        <a href='https://www.linkedin.com/shareArticle?mini=true&url=POST_URL' target='_blank'>LinkedIn</a>
    </div>
    """

    full_content = f"""
    <h2>Summary</h2>
    <p>{summary}</p><br>
    <img src='{image_url}' alt='{title}' width='800' /><br>
    {content}<br>
    {hashtags}<br>
    {social_share_buttons}
    """

    post_data = {
        "title": title,
        "content": full_content,
        "status": "publish"
    }

    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json"
    }

    response = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", json=post_data, headers=headers)

    if response.status_code == 201:
        print(f"✅ Successfully posted: {title}")
    else:
        print(f"❌ Failed to post: {title}")
        print(f"⚠️ HTTP Status Code: {response.status_code}")
        print(f"⚠️ Response Content: {response.text}")  # Print the API response for debugging

    return response.status_code == 201


# --------------------- MAIN AUTO POST FUNCTION ---------------------
def auto_post():
    for _ in range(5):  # Limits to 5 posts to avoid overload
        topic = random.choice(fetch_trending_keywords())
        summary, content = generate_article(topic)
        post_to_wordpress(topic, summary, content, topic)
        print(f"✅ Posted article on: {topic}")
        time.sleep(300)  # Runs every 5 minutes

auto_post()
