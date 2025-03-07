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

# Check if all necessary environment variables are set
if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD, OPENAI_API_KEY]):
    raise ValueError("❌ Missing required environment variables. Check WP_URL, WP_USERNAME, WP_APP_PASSWORD, and OPENAI_API_KEY.")

# ------------------- TRENDING TOPICS FROM GOOGLE -------------------
def get_trending_topics():
    try:
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
        
        if not trending_topics:
            return "SEO Best Practices"
        
        topic = random.choice(trending_topics).capitalize()
        print(f"🔍 Selected Trending Topic: {topic}")
        return topic
    except Exception as e:
        print(f"❌ Error fetching trending topics: {e}")
        return "SEO Best Practices"

# -------------------- AI ARTICLE GENERATION --------------------
def generate_article(topic):
    try:
        openai.api_key = OPENAI_API_KEY
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
        content = response["choices"][0]["message"]["content"]
        print("✅ Article generated successfully.")
        return content
    except Exception as e:
        print(f"❌ Error generating article: {e}")
        return "Error generating content."

# --------------------- MULTIPLE IMAGE SOURCES ---------------------
def get_image(query):
    for source, url in {
        "Unsplash": f"https://api.unsplash.com/photos/random?query={query}&client_id={UNSPLASH_ACCESS_KEY}",
        "Pexels": f"https://api.pexels.com/v1/search?query={query}&per_page=1",
        "Pixabay": f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&per_page=3"
    }.items():
        try:
            headers = {"Authorization": PEXELS_API_KEY} if source == "Pexels" else {}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if source == "Unsplash":
                    return data['urls']['regular']
                elif source == "Pexels" and data.get('photos'):
                    return data['photos'][0]['src']['original']
                elif source == "Pixabay" and data.get('hits'):
                    return data['hits'][0]['largeImageURL']
        except Exception as e:
            print(f"⚠️ {source} Image Fetch Failed: {e}")
    return f"https://source.unsplash.com/1200x800/?{query}"

# ----------------- POST ARTICLE TO WORDPRESS -----------------
def post_to_wordpress(title, content, image_url):
    try:
        credentials = requests.auth._basic_auth_str(WP_USERNAME, WP_APP_PASSWORD)
        post = {
            "title": title,
            "content": f"<img src='{image_url}' alt='{title}'/><br>{content}<br><br><strong>🚀 Explore our powerful SEO tools at <a href='https://seotoolfusion.com'>SEO Tool Fusion</a>!</strong>",
            "status": "publish",
            "categories": ["SEO", "Digital Marketing", "YouTube SEO", "Affiliate Marketing"],
            "tags": title.lower().split()
        }
        response = requests.post(WP_URL, json=post, headers={"Authorization": credentials})
        print(f"📡 API Response Code: {response.status_code}")
        if response.status_code == 201:
            print(f"✅ Successfully posted: {title}")
        else:
            print(f"❌ Failed to post: {response.text}")
    except Exception as e:
        print(f"❌ Error posting to WordPress: {e}")

# --------------------- MAIN AUTO POST FUNCTION ---------------------
def auto_post():
    trending_topic = get_trending_topics()
    content = generate_article(trending_topic)
    image_url = get_image(trending_topic)
    post_to_wordpress(trending_topic, content, image_url)

# ------------------------ SCHEDULE TASK ------------------------
schedule.every(10).seconds.do(auto_post)  # Adjust interval for testing
print("🚀 Ultimate Auto Article Poster is running...")

while True:
    schedule.run_pending()
    time.sleep(60)
