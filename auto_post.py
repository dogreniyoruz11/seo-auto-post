import os
import requests
import openai
import google.generativeai as genai
import random
import time
import schedule
from pytrends.request import TrendReq
from requests.auth import HTTPBasicAuth

# ----------------------- CONFIGURATION -----------------------
WP_URL = os.getenv("WP_URL")
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD]):
    raise ValueError("❌ Missing required environment variables. Check WP_URL, WP_USERNAME, WP_APP_PASSWORD.")

# ------------------- TRENDING TOPICS FROM GOOGLE -------------------
def get_trending_topics():
    """Fetch trending topics from Google Trends."""
    try:
        print("🔍 Fetching trending topics from Google Trends...")
        pytrends = TrendReq(hl='en-US', tz=360)
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
            time.sleep(5)  # Prevents IP bans
            pytrends.build_payload(group, timeframe='now 7-d', geo='US')
            trends = pytrends.related_queries()

            if not trends or trends == {}:
                continue  

            for kw in group:
                if trends.get(kw) and trends[kw]['top'] is not None:
                    queries = trends[kw]['top']['query'].tolist()
                    if queries:
                        trending_topics.extend(queries)

        if not trending_topics:
            print("⚠️ No trending topics found. Using default topic.")
            return "SEO Best Practices"

        topic = random.choice(trending_topics).capitalize()
        print(f"✅ Selected Trending Topic: {topic}")
        return topic

    except Exception as e:
        print(f"❌ Google Trends failed (Possible ban or API issue): {e}")
        return "SEO Best Practices"

# -------------------- AI ARTICLE GENERATION --------------------
def generate_article(topic):
    """Generates an AI-powered SEO-optimized article using OpenAI or Gemini."""
    try:
        print(f"📝 Generating article for: {topic}")

        if OPENAI_API_KEY:
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
            print("✅ Article generated successfully with OpenAI.")
            return content

    except Exception as e:
        print(f"⚠️ OpenAI failed: {e}. Trying Gemini...")
        
        try:
            if GEMINI_API_KEY:
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-pro")
                response = model.generate_content(f"Write an SEO-optimized article about {topic}.")
                print("✅ Article generated successfully with Gemini.")
                return response.text
        except Exception as e:
            print(f"❌ Both OpenAI and Gemini failed: {e}")
            return "Error generating content."

# --------------------- MULTIPLE IMAGE SOURCES ---------------------
def get_image(query):
    """Fetches an image from Unsplash, Pexels, or Pixabay."""
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
                    return data["urls"]["regular"]
                elif source == "Pexels" and data.get("photos"):
                    return data["photos"][0]["src"]["original"]
                elif source == "Pixabay" and data.get("hits"):
                    return data["hits"][0]["largeImageURL"]
        except Exception as e:
            print(f"⚠️ {source} Image Fetch Failed: {e}")
    return f"https://source.unsplash.com/1200x800/?{query}"

# ----------------- POST ARTICLE TO WORDPRESS -----------------
def post_to_wordpress(title, content, image_url):
    """Posts the generated article to WordPress."""
    try:
        credentials = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)

        post = {
            "title": title,
            "content": f"<img src='{image_url}' alt='{title}'/><br>{content}<br><br><strong>🚀 Explore our powerful SEO tools at <a href='https://seotoolfusion.com'>SEO Tool Fusion</a>!</strong>",
            "status": "publish",
            "categories": [1, 2, 3],
            "tags": [10, 20, 30]
        }

        response = requests.post(WP_URL, json=post, auth=credentials)

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
schedule.every(10).hours.do(auto_post)  # Reduced frequency to avoid bans
print("🚀 Ultimate Auto Article Poster is running...")

while True:
    try:
        schedule.run_pending()
        time.sleep(60)
    except KeyboardInterrupt:
        print("🛑 Script stopped by user.")
        break
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
