import requests
import os
import feedparser
from dotenv import load_dotenv
from urllib.parse import quote
import trafilatura
from googlenewsdecoder import new_decoderv1
import ollama
import asyncio

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") #llama3.2

async def analyze_bias(article: dict) -> dict:
    content = get_article_content(article['url']) if article['url'] else ""

    prompt = f"""
    Analyze the following news article for media bias and return a structured response.

    Title: {article['title']}
    Content: {content}

    Please provide:
    1. Bias Score: A number from -10 (far left) to +10 (far right), 0 = neutral
    2. Bias Label: One of [⬅️⬅️⬅️  Far Left, ⬅️ Left, ◀️ Center-Left, ⚪️ Center, Center-Right ▶️, Right ➡️, Far Right ➡️➡️➡️]
    3. Bias Indicators: List of specific words/phrases that indicate bias
    4. Summary: 2-3 sentence explanation of your analysis

    Respond in this exact format:
    SCORE: <number>
    LABEL: <label>
    INDICATORS: <comma separated list>
    SUMMARY: <your summary>
    """

    try:
        client = ollama.AsyncClient()
        response = await client.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt}]
        )
        print(response['message']['content'])
        # return parse_response(response['message']['content'])
        # return response['message']['content']
        bias = response['message']['content']
    except Exception as e:
        print(f"Ollama error: {e}")
        return {
            'score': 0,
            'label': 'Unavailable',
            'indicators': [],
            'summary': 'Analysis unavailable. Make sure Ollama is running.',
        }

    return {**article, "bias": bias}


def analyze_all_articles(articles: list) -> list:
    async def run():
        tasks = [analyze_bias(article) for article in articles]
        return await asyncio.gather(*tasks)

    return asyncio.run(run())

def parse_response(text: str) -> dict:
    result = {
        'score': 0,
        'label': 'Center',
        'indicators': [],
        'summary': '',
    }

    for line in text.strip().splitlines():
        if line.startswith('SCORE:'):
            try:
                result['score'] = float(line.replace('SCORE:', '').strip())
            except ValueError:
                pass
        elif line.startswith('LABEL:'):
            result['label'] = line.replace('LABEL:', '').strip()
        elif line.startswith('INDICATORS:'):
            raw = line.replace('INDICATORS:', '').strip()
            result['indicators'] = [i.strip() for i in raw.split(',') if i.strip()]
        elif line.startswith('SUMMARY:'):
            result['summary'] = line.replace('SUMMARY:', '').strip()

    return result

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

        articles.append({
            "title": entry.title,
            "source": "Google News",
            "url": real_url,
            # "content": get_article_content(real_url)
            # "analyze": analyze_bias(title=entry.title, url=real_url)
        })

    articles = analyze_all_articles(articles)

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
            "content": get_article_content(article["url"])
        })

    return articles


def get_related_news(topic):

    google_articles = get_google_news(topic)
    api_articles = get_newsapi_news(topic)

    combined = google_articles 
    # + api_articles

    seen = set()
    unique_articles = []

    for article in combined:
        title = article["title"].lower()

        if title not in seen:
            unique_articles.append(article)
            seen.add(title)

    return unique_articles
