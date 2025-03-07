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
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# ✅ Configure APIs
openai.api_key = OPENAI_API_KEY
if GOOGLE_GEMINI_API_KEY:
    genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
else:
    print("❌ WARNING: GOOGLE_GEMINI_API_KEY is missing!")

# -------------------- FETCH TRENDING KEYWORDS --------------------
def fetch_trending_keywords():
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
        pytrends.build_payload(group, timeframe='now 7-d')
        trends = pytrends.related_queries()
        for kw in group:
            if trends.get(kw) and trends[kw]['top'] is not None:
                trending_keywords.extend(trends[kw]['top']['query'].tolist())
    return trending_keywords[:10]

# -------------------- FETCH AND EMBED YOUTUBE VIDEO --------------------
def fetch_youtube_video(topic):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={topic}&type=video&key={YOUTUBE_API_KEY}&maxResults=1"
    response = requests.get(url).json()
    if "items" in response and response["items"]:
        video_id = response["items"][0]["id"]["videoId"]
        return f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}?rel=0&autoplay=0" allowfullscreen></iframe>'
    return ""

# -------------------- FETCH IMAGES --------------------
def fetch_images(topic, count=5):
    sources = [
        ("unsplash", f"https://api.unsplash.com/photos/random?query={topic}&count={count}&client_id={UNSPLASH_ACCESS_KEY}"),
        ("pexels", f"https://api.pexels.com/v1/search?query={topic}&per_page={count}"),
        ("pixabay", f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={topic}&per_page={count}")
    ]
    headers = {"Authorization": PEXELS_API_KEY} if PEXELS_API_KEY else {}
    images = []
    for source, url in sources:
        try:
            response = requests.get(url, headers=headers if source == "pexels" else {}).json()
            if source == "unsplash":
                images.extend([img["urls"]["regular"] for img in response])
            elif source == "pexels":
                images.extend([img["src"]["medium"] for img in response["photos"]])
            elif source == "pixabay":
                images.extend([img["webformatURL"] for img in response["hits"]])
        except:
            continue
    return images[:count]

# -------------------- AI ARTICLE GENERATION --------------------
def generate_article(topic):
    prompt = f"Write a 800-1600 word SEO-optimized article on '{topic}' with headings, images, and videos. Include a summary and popular hashtags."
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000
    )
    return response["choices"][0]["message"]["content"]

# --------------------- AUTO POST TO WORDPRESS ---------------------
def post_to_wordpress(title, content, topic):
    credentials = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    video_embed = fetch_youtube_video(topic)
    images = fetch_images(topic, count=5)
    formatted_content = f"""
    <h1>{title}</h1>
    {''.join([f'<img src="{img}" alt="{title}" style="max-width:100%; height:auto;"/><br>' for img in images])}
    <h2>Summary</h2>
    <p>{content[:300]}</p>
    <h2>Main Content</h2>
    <p>{content[300:]}</p>
    <h2>Watch Related Video</h2>
    {video_embed}
    <h2>Share This Post</h2>
    <a href="https://www.facebook.com/sharer/sharer.php?u={WP_URL}">Facebook</a> |
    <a href="https://twitter.com/intent/tweet?url={WP_URL}&text={title}">Twitter</a> |
    <a href="https://www.linkedin.com/sharing/share-offsite/?url={WP_URL}">LinkedIn</a>
    """
    api_url = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/posts"
    post_data = {"title": title, "content": formatted_content, "status": "publish"}
    response = requests.post(api_url, json=post_data, headers={"Content-Type": "application/json"}, auth=credentials)
    if response.status_code == 201:
        print(f"✅ Successfully posted: {title}")
    else:
        print(f"❌ Failed to post: {title}. HTTP {response.status_code}")

# --------------------- MAIN AUTO POST FUNCTION ---------------------
def auto_post():
    topic = random.choice(fetch_trending_keywords())
    content = generate_article(topic)
    post_to_wordpress(topic, content, topic)

# --------------------- SCHEDULED POSTING ---------------------
schedule.every(2).minutes.do(auto_post)

while True:
    schedule.run_pending()
    time.sleep(60)
