import requests
import os
import feedparser
from dotenv import load_dotenv
from urllib.parse import quote
from functools import lru_cache

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")


# ----------------------------
# GOOGLE NEWS
# ----------------------------
def get_google_news(topic):

    encoded_topic = quote(topic)

    url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(url)

    articles = []

    for entry in feed.entries[:6]:

        source = entry.get("source", {}).get("title", "Google News")

        articles.append({
            "title": entry.title,
            "source": source,
            "url": entry.link,
            "published": entry.get("published", ""),
            "summary": entry.get("summary", "")
        })

    return articles


# ----------------------------
# NEWS API
# ----------------------------
def get_newsapi_news(topic):

    url = "https://newsapi.org/v2/everything"

    params = {
        "q": topic,
        "searchIn": "title,description",
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": 6,
        "excludeDomains": "reddit.com,medium.com",
        "apiKey": NEWS_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=6)
    except:
        return []

    if response.status_code != 200:
        return []

    data = response.json()

    articles = []

    for article in data.get("articles", []):

        articles.append({
            "title": article["title"],
            "source": article["source"]["name"],
            "url": article["url"],
            "published": article.get("publishedAt", ""),
            "summary": article.get("description", "")
        })

    return articles


# ----------------------------
# COMBINE + CACHE
# ----------------------------
@lru_cache(maxsize=50)
def get_related_news(topic):

    google_articles = get_google_news(topic)
    api_articles = get_newsapi_news(topic)

    combined = google_articles + api_articles

    seen = set()
    unique_articles = []

    for article in combined:

        title = article["title"].lower()

        if title not in seen:
            unique_articles.append(article)
            seen.add(title)

    return unique_articles
