import requests
import os
import feedparser
from dotenv import load_dotenv
from urllib.parse import quote
from functools import lru_cache
import trafilatura
from googlenewsdecoder import new_decoderv1
import ollama
import asyncio

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


# ----------------------------
# ARTICLE CONTENT EXTRACTION
# ----------------------------
def get_article_content(url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=8)
        content = trafilatura.extract(response.text)

        return content or ""

    except Exception as e:
        print(f"Failed to fetch content: {e}")
        return ""


# ----------------------------
# OLLAMA BIAS ANALYSIS
# ----------------------------
async def analyze_bias(article: dict) -> dict:

    content = get_article_content(article["url"]) if article["url"] else ""

    prompt = f"""
Analyze the following news article for political or emotional bias.

Title: {article['title']}
Content: {content[:2000]}

Return exactly:

SCORE: <number between -10 and +10, use the FULL range aggressively — obvious tabloid or opinionated pieces should score 8-10, balanced reporting should score around 0, truly neutral wire reports score -10>
LABEL: <Far Left | Left | Center-Left | Center | Center-Right | Right | Far Right>
CLAIMS: <2-5 claims stated>
INDICATORS: <comma separated list>
SUMMARY: <short explanation>
"""

    try:
        client = ollama.AsyncClient()

        response = await client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        parsed = parse_response(response["message"]["content"])

    except Exception as e:
        print(f"Ollama error: {e}")

        parsed = {
            "score": 0,
            "label": "Unavailable",
            "claims": [],
            "indicators": [],
            "summary": "Bias analysis unavailable"
        }

    return {**article, "bias": parsed}


def parse_response(text: str) -> dict:

    result = {
        "score": 0,
        "label": "Center",
        "claims":[],
        "indicators": [],
        "summary": ""
    }

    for line in text.strip().splitlines():

        if line.startswith("SCORE:"):
            try:
                result["score"] = float(line.replace("SCORE:", "").strip())
            except:
                pass

        elif line.startswith("LABEL:"):
            result["label"] = line.replace("LABEL:", "").strip()

        elif line.startswith("CLAIMS:"):
            raw = line.replace("CLAIMS:", "").strip()
            result["claims"] = [i.strip() for i in raw.split(",") if i.strip()]

        elif line.startswith("INDICATORS:"):
            raw = line.replace("INDICATORS:", "").strip()
            result["indicators"] = [i.strip() for i in raw.split(",") if i.strip()]

        elif line.startswith("SUMMARY:"):
            result["summary"] = line.replace("SUMMARY:", "").strip()

    return result


def analyze_all_articles(articles: list) -> list:

    async def run():
        tasks = [analyze_bias(article) for article in articles]
        return await asyncio.gather(*tasks)

    return asyncio.run(run())

def group_summary_bias(articles: dict, topic: str) -> dict:


    prompt = f"""
Create groups of the articles for political or emotional bias to answer user question: {topic}.

All articles to be analyzed:
---
{articles}
---

Return exactly:

How many groups of views: <between 1-4>
View: <list the views in one sentence each>
SUMMARY: <short summary of those findings and conclude the user query wether the question is bias or not>
"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        return response["message"]["content"]

    except Exception as e:
        print(f"Ollama error: {e}")

        return {
            "score": 0,
            "label": "Unavailable",
            "indicators": [],
            "summary": "Summary bias analysis unavailable"
        }


# ----------------------------
# GOOGLE NEWS
# ----------------------------
EXCLUDED_DOMAINS = [
    # Social media
    "reddit.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "linkedin.com",
    "pinterest.com",

    # Blogs & opinion
    "medium.com",
    "substack.com",
    "blogspot.com",
    "wordpress.com",
    "tumblr.com",
    "quora.com",

    # Fringe & extremist
    "4chan.org",
    "8kun.top",
    "gab.com",
    "parler.com",

    # Known misinformation
    "breitbart.com",
    "infowars.com",
    "naturalnews.com",
    "beforeitsnews.com",
    "thegatewaypundit.com",
    "zerohedge.com",

    # State propaganda
    "rt.com",
    "sputniknews.com",
]

def is_excluded(url: str) -> bool:
    return any(domain in url for domain in EXCLUDED_DOMAINS)

def get_google_news(topic):

    encoded_topic = quote(topic)

    url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(url)

    articles = []

    for entry in feed.entries[:10]:
        if is_excluded(entry.link):
            continue  # skip excluded domains

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
            "summary": entry.get("summary", "")
        })

    # run bias analysis
    articles = analyze_all_articles(articles)

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
        "excludeDomains": "reddit.com,medium.com,twitter.com,x.com,facebook.com,instagram.com,tiktok.com,youtube.com,substack.com,blogspot.com,wordpress.com,tumblr.com,quora.com,pinterest.com,linkedin.com,4chan.org,8kun.top,gab.com,parler.com,breitbart.com,infowars.com,naturalnews.com,beforeitsnews.com,thegatewaypundit.com,zerohedge.com,rt.com,sputniknews.com",
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


    # run bias analysis in newsapi too
    articles = analyze_all_articles(articles)

    return articles



# ----------------------------
# COMBINE + CACHE
# ----------------------------
@lru_cache(maxsize=50)
def get_related_news(topic):

    google_articles = get_google_news(topic)
    api_articles = get_newsapi_news(topic)

    combined = google_articles + api_articles

    # do summary bias analysis
    group_summary = group_summary_bias(combined,topic=topic)
    #

    seen = set()
    unique_articles = []

    for article in combined:

        title = article["title"].lower()

        if title not in seen:
            unique_articles.append(article)
            seen.add(title)
    
    results = []
    results.append(unique_articles)
    results.append(group_summary)

    return results
