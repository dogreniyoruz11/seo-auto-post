import os
import random
import requests
import openai
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
            trends = pytrends.related_queries()
            
            for kw in group:
                # Check if data exists to prevent errors
                if kw in trends and trends[kw] and trends[kw]['top'] is not None:
                    queries = trends[kw]['top']['query'].tolist()
                    trending_keywords.extend(queries)
                    
        except Exception as e:
            print(f"⚠️ Error fetching trends for {group}: {e}")
    
    if not trending_keywords:
        print("❌ No trending keywords found. Using fallback default keywords.")
        trending_keywords = ["SEO strategies", "Google ranking tips", "YouTube video SEO", "AI marketing automation"]

    return trending_keywords[:10]  # Return top 10 results


# ------------------- AI-BASED HIDDEN KEYWORDS -------------------
def discover_unmined_keywords(topic):
    prompt = f"Generate 10 untapped, high-traffic, zero-competition keywords related to '{topic}'."
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )
    return response["choices"][0]["message"]["content"].split("\n")

# -------------------- AI ARTICLE GENERATION --------------------
def generate_article(topic):
    summary_prompt = f"Generate a 3-4 sentence summary of an article about '{topic}'."
    summary = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": summary_prompt}],
        max_tokens=100
    )["choices"][0]["message"]["content"]
    
    content_prompt = f"Write a 1500-2000 word engaging SEO-optimized article on '{topic}'. Include a Table of Contents."
    content = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": content_prompt}],
        max_tokens=3000
    )["choices"][0]["message"]["content"]
    
    return summary, content

# --------------------- IMAGE OPTIMIZATION ---------------------
def fetch_and_compress_image(topic):
    image_url = fetch_image(topic)  # Fetch image from API
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    img = img.resize((800, int(img.height * (800 / img.width))))  # Keep aspect ratio
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=75, optimize=True)
    return upload_to_wordpress(buffer.getvalue())  # Upload & return compressed image URL

# --------------------- AI-GENERATED HASHTAGS ---------------------
def generate_hashtags(topic):
    prompt = f"Generate 5 relevant hashtags for a blog post on '{topic}'."
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50
    )
    return response["choices"][0]["message"]["content"]

# --------------------- RELATED ARTICLES ---------------------
def fetch_related_articles(topic):
    search_url = f"{WP_URL}/wp-json/wp/v2/posts?search={topic}&per_page=3"
    response = requests.get(search_url)
    if response.status_code == 200:
        posts = response.json()
        related_articles_html = "<h3>Related Articles</h3><ul>"
        for post in posts:
            related_articles_html += f"<li><a href='{post['link']}'>{post['title']['rendered']}</a></li>"
        related_articles_html += "</ul>"
        return related_articles_html
    return ""

# --------------------- AUTO POST TO WORDPRESS ---------------------
def post_to_wordpress(title, summary, content, topic):
    credentials = requests.auth._basic_auth_str(WP_USERNAME, WP_APP_PASSWORD)
    
    image_url = fetch_and_compress_image(topic)
    related_articles = fetch_related_articles(topic)
    hashtags = generate_hashtags(topic)
    
    social_share_buttons = f"""
    <h3>📢 Share This Article</h3>
    <div class='social-share'>
        <a href='https://www.facebook.com/sharer/sharer.php?u=POST_URL' target='_blank'>Facebook</a> |
        <a href='https://twitter.com/intent/tweet?text={title}&url=POST_URL' target='_blank'>Twitter</a> |
        <a href='https://www.linkedin.com/shareArticle?mini=true&url=POST_URL' target='_blank'>LinkedIn</a>
    </div>
    """

    monetized_content = insert_monetization(content)
    full_content = f"""
    <h2>Summary</h2>
    <p>{summary}</p><br>
    <img src='{image_url}' alt='{title}' width='800' /><br>
    {monetized_content}<br>
    {hashtags}<br>
    {related_articles}<br>
    {social_share_buttons}
    """

    post = {
        "title": title,
        "content": full_content,
        "status": "publish"
    }

    response = requests.post(WP_URL, json=post, headers={"Authorization": credentials})
    return response.status_code == 201

# --------------------- MAIN AUTO POST FUNCTION ---------------------
def auto_post():
    while True:
        topic = random.choice(fetch_trending_keywords())
        unmined_keywords = discover_unmined_keywords(topic)
        summary, content = generate_article(topic)
        post_to_wordpress(topic, summary, content, topic)
        print(f"✅ Posted article on: {topic}")
        time.sleep(300)  # Runs every 5 minutes

# Start the loop
auto_post()
