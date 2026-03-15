import os
import feedparser
import ollama

from dotenv import load_dotenv
from urllib.parse import quote
from functools import lru_cache
from googlenewsdecoder import new_decoderv1

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

ollama_client = ollama.Client()


# ----------------------------
# BIAS ANALYSIS
# ----------------------------
def analyze_bias(article):

    prompt = f"""
Analyze the bias in this news article.

Title: {article['title']}
Summary: {article.get('summary','')}

Estimate what percentage of the article appears biased.

Return exactly in this format:

BIAS_PERCENT: <number 0-100>
EXPLANATION: <short explanation of why the article is biased or not>
"""

    try:

        response = ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2}
        )

        parsed = parse_response(response["message"]["content"])

    except Exception as e:

        print("Ollama error:", e)

        parsed = {
            "percent": 0,
            "explanation": "Bias analysis unavailable."
        }

    return {**article, "bias": parsed}


# ----------------------------
# PARSE RESPONSE
# ----------------------------
def parse_response(text):

    result = {
        "percent": 0,
        "explanation": ""
    }

    for line in text.splitlines():

        if "BIAS_PERCENT" in line:
            try:
                result["percent"] = float(line.split(":")[1].strip())
            except:
                pass

        elif "EXPLANATION" in line:
            result["explanation"] = line.split(":",1)[1].strip()

    return result


# ----------------------------
# GOOGLE NEWS FETCH
# ----------------------------
def get_google_news(topic):

    encoded = quote(topic)

    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(url)

    articles = []

    seen = set()

    for entry in feed.entries:

        try:
            decoded = new_decoderv1(entry.link)
            real_url = decoded.get("decoded_url", entry.link)
        except:
            real_url = entry.link

        if real_url in seen:
            continue

        seen.add(real_url)

        source = entry.get("source", {}).get("title", "Google News")

        articles.append({
            "title": entry.title,
            "source": source,
            "url": real_url,
            "published": entry.get("published", ""),
            "summary": entry.get("summary", "")
        })

        if len(articles) >= 10:
            break

    return articles


# ----------------------------
# MAIN SEARCH FUNCTION
# ----------------------------
@lru_cache(maxsize=200)
def get_related_news(topic):

    return get_google_news(topic)
