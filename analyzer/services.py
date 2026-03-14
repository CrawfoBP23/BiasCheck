import requests
import os
import feedparser
from dotenv import load_dotenv
from urllib.parse import quote
import trafilatura
from googlenewsdecoder import new_decoderv1

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")


def get_article_content(url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)

        content = trafilatura.extract(response.text)

        return content or ""

    except Exception as e:
        print(f"Failed to fetch content: {e}")
        return ""


def get_google_news(topic):

    encoded_topic = quote(topic)

    url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(url)

    articles = []

    for entry in feed.entries[:5]:

        try:
            decoded = new_decoderv1(entry.link)
            real_url = decoded.get("decoded_url", entry.link)
        except Exception as e:
            print(f"Could not decode URL: {e}")
            real_url = entry.link

        source = entry.get("source", {}).get("title", "Google News")

        articles.append({
            "title": entry.title,
            "source": source,
            "url": real_url,
            "published": entry.get("published", ""),
            "summary": entry.get("summary", ""),
            "content": get_article_content(real_url)
        })

    return articles


def get_newsapi_news(topic):

    url = "https://newsapi.org/v2/everything"

    params = {
        "q": topic,
        "searchIn": "title,description",
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": 15,
        "excludeDomains": "reddit.com,medium.com",
        "apiKey": NEWS_API_KEY
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return []

    data = response.json()

    articles = []

    for article in data.get("articles", []):

        articles.append({
            "title": article["title"],
            "source": article["source"]["name"],
            "url": article["url"],
            "summary": article.get("description", ""),
            "published": article.get("publishedAt", ""),
            "content": get_article_content(article["url"])
        })

    return articles


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
