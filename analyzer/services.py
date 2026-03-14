import requests
import os
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")


def get_related_news(topic):

    url = "https://newsapi.org/v2/everything"

    params = {
        "q": topic,
        "apiKey": NEWS_API_KEY,
        "pageSize": 100,
        "language": "en",
        "searchIn": ["title", "description"],
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
            "description": article["description"],
        })

    print(articles)

    return articles
