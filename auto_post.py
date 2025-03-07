import os
import requests
import openai
import random
import time
from pytrends.request import TrendReq
import schedule

# ----------------------- CONFIGURATION -----------------------

WP_URL = os.getenv("WP_URL")
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")


# ------------------- TRENDING TOPICS FROM GOOGLE -------------------
def get_trending_topics():
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

    trending_topics = []

    for group in keyword_groups:
        pytrends.build_payload(group, timeframe='now 7-d')
        trends = pytrends.related_queries()

        for kw in group:
            if trends.get(kw) and trends[kw]['top'] is not None:
                queries = trends[kw]['top']['query'].tolist()
                trending_topics.extend(queries)

    return random.choice(trending_topics).capitalize()

# -------------------- AI ARTICLE GENERATION --------------------
def generate_article(topic):
    prompt = f"""
    Write a detailed, engaging, and SEO-optimized article on "{topic}" including:
    - Keyword-rich title
    - Table of Contents
    - Clear introduction
    - At least 3 main sections (use H2 and H3 headings)
    - Bullet points and numbered lists for clarity
    - Conclusion with a strong Call-to-Action encouraging readers to explore powerful SEO tools at seotoolfusion.com
    """
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500
    )
    return response["choices"][0]["message"]["content"]

# --------------------- MULTIPLE IMAGE SOURCES ---------------------
def get_image(query):
    # Try Unsplash first
    unsplash_url = f"https://api.unsplash.com/photos/random?query={query}&client_id={UNSPLASH_ACCESS_KEY}"
    response = requests.get(unsplash_url)
    if response.status_code == 200:
        return response.json()['urls']['regular']

    # Try Pexels if Unsplash fails
    pexels_headers = {"Authorization": PEXELS_API_KEY}
    pexels_url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
    response = requests.get(pexels_url, headers=pexels_headers)
    if response.status_code == 200:
        photos = response.json().get('photos', [])
        if photos:
            return photos[0]['src']['original']

    # Try Pixabay as last resort
    pixabay_url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&per_page=3"
    response = requests.get(pixabay_url)
    if response.status_code == 200:
        hits = response.json().get('hits', [])
        if hits:
            return hits[0]['largeImageURL']

    # Final fallback
    return f"https://source.unsplash.com/1200x800/?{query}"

# ----------------- POST ARTICLE TO WORDPRESS -----------------
def post_to_wordpress(title, content, image_url):
    credentials = requests.auth._basic_auth_str(WP_USERNAME, WP_APP_PASSWORD)

    post = {
        "title": title,
        "content": f"<img src='{image_url}' alt='{title}'/><br>{content}<br><br><strong>🚀 Explore our powerful SEO tools at <a href='https://seotoolfusion.com'>SEO Tool Fusion</a>!</strong>",
        "status": "publish",
        "categories": ["SEO", "Digital Marketing", "YouTube SEO", "Affiliate Marketing"],
        "tags": title.lower().split()
    }

    response = requests.post(WP_URL, json=post, headers={"Authorization": credentials})

    if response.status_code == 201:
        print(f"✅ Successfully posted: {title}")
    else:
        print(f"❌ Failed to post: {response.text}")

# --------------------- MAIN AUTO POST FUNCTION ---------------------
def auto_post():
    trending_topic = get_trending_topics()
    print(f"🚀 Writing about trending topic: {trending_topic}")

    content = generate_article(trending_topic)
    image_url = get_image(trending_topic)
    post_to_wordpress(trending_topic, content, image_url)

# ------------------------ SCHEDULE TASK ------------------------
schedule.every(2).minutes.do(auto_post)

print("🚀 Ultimate Auto Article Poster is running...")

while True:
    schedule.run_pending()
    time.sleep(60)

