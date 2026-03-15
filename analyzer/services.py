import requests
import os
import feedparser
import time
from dotenv import load_dotenv
from urllib.parse import quote
from functools import lru_cache
import trafilatura
from googlenewsdecoder import new_decoderv1
# import ollama
from groq import AsyncGroq, Groq
import asyncio
import datetime

load_dotenv()

# Rate limit: retry 429 with backoff; max concurrent article analyses
GROQ_MAX_RETRIES = 4
GROQ_RETRY_BASE_SEC = 8
GROQ_MAX_CONCURRENT = 3

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL","phi3:mini")
GROQ_MODEL = "openai/gpt-oss-20b"


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
# RATE LIMIT HELPERS
# ----------------------------
def _is_rate_limit_error(e: Exception) -> bool:
    code = getattr(e, "status_code", None) or getattr(getattr(e, "response", None), "status_code", None)
    if code == 429:
        return True
    msg = str(e).lower()
    return "429" in msg or "rate limit" in msg


def _retry_after(e: Exception) -> float:
    try:
        r = getattr(e, "response", None)
        if r is not None:
            after = r.headers.get("retry-after")
            if after:
                return float(after)
    except Exception:
        pass
    return GROQ_RETRY_BASE_SEC


# ----------------------------
# OLLAMA BIAS ANALYSIS
# ----------------------------
async def _analyze_bias_one(article: dict, semaphore: asyncio.Semaphore, client: AsyncGroq) -> dict:
    async with semaphore:
        content = get_article_content(article["url"]) if article["url"] else ""

        print(f"[✓] get article content of '{article['url']}'... finished at {datetime.datetime.now().time().strftime('%H:%M:%S')}")
        prompt = f"""
Analyze the following news article for political or emotional bias.

Title: {article['title']}
Content: {content[:2000]}

First decide: was there substantive article content to analyze? Answer no if the page had only a paywall, "enable JavaScript", "disable ad blocker", login prompt, or too little real reporting to assess bias.

The bias score is on a scale of 0 to 10 only (no negatives). 0 = no bias, 10 = heavily biased. You MUST use the full range: if the article is straight factual reporting with no political or emotional slant, give 0. Do not assume articles are somewhat biased; many deserve 0–2. Only use higher scores when there is real slant, opinion, or advocacy.

Return exactly (use the FULL 0-10 range for EVIDENCE and PERSUASIVE; differentiate clearly between articles):

ANALYZABLE: <yes or no — no if content was not substantive or was only placeholder/instructions>
SCORE: <number 0 to 10 only: 0 = no bias (factual, balanced, neutral wire style), 5 = moderate slant, 10 = heavily biased/opinion piece — use the full range; give 0 when appropriate>
LABEL: <Far Left | Left | Center-Left | Center | Center-Right | Right | Far Right | No Political Bias>
EVIDENCE: <single number 0-10 only; 0=purely speculative/opinion, 10=strongly evidence-based and factual; use decimals if needed e.g. 3 or 7.5>
PERSUASIVE: <single number 0-10 only; 0=neutral/balanced, 10=highly persuasive/advocacy; use decimals if needed>
CLAIMS: <2-5 claims stated>
INDICATORS: <comma separated list>
REASONS: <2-4 short phrases explaining why this bias score, separated by | e.g. Emotional language detected | Selective focus on conflict | Missing opposing perspectives>
SUMMARY: <short explanation>
"""
        last_error = None
        for attempt in range(GROQ_MAX_RETRIES):
            try:
                response = await client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}]
                )
                parsed = parse_response(response.choices[0].message.content)
                return {**article, "bias": parsed}
            except Exception as e:
                last_error = e
                if _is_rate_limit_error(e) and attempt < GROQ_MAX_RETRIES - 1:
                    wait = _retry_after(e) * (2 ** attempt)
                    print(f"Rate limit hit, retrying in {wait:.0f}s (attempt {attempt + 1}/{GROQ_MAX_RETRIES})...")
                    await asyncio.sleep(wait)
                else:
                    break
        print(f"Ollama error: {last_error}")
        parsed = {
            "analyzable": True,
            "score": 0,
            "label": "Unavailable",
            "evidence": 5,
            "persuasive": 5,
            "claims": [],
            "indicators": [],
            "reasons": [],
            "summary": "Bias analysis unavailable"
        }
        return {**article, "bias": parsed}


async def analyze_bias(article: dict) -> dict:
    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    try:
        return await _analyze_bias_one(article, asyncio.Semaphore(1), client)
    finally:
        for attr in ("_client", "_http_client", "client"):
            if hasattr(client, attr) and hasattr(getattr(client, attr), "aclose"):
                try:
                    await getattr(client, attr).aclose()
                except Exception:
                    pass
                break


def parse_response(text: str) -> dict:

    result = {
        "analyzable": True,
        "score": 0,
        "label": "Center",
        "evidence": 5,
        "persuasive": 5,
        "claims":[],
        "indicators": [],
        "reasons": [],
        "summary": ""
    }

    for line in text.strip().splitlines():
        if line.strip().upper().startswith("ANALYZABLE:"):
            val = line.split(":", 1)[-1].strip().upper()
            result["analyzable"] = val in ("YES", "Y", "1", "TRUE")

        elif line.startswith("SCORE:"):
            try:
                raw = line.replace("SCORE:", "").strip()
                result["score"] = max(0, min(10, float(raw)))
            except (TypeError, ValueError):
                pass

        elif line.startswith("LABEL:"):
            result["label"] = line.replace("LABEL:", "").strip()

        elif line.strip().upper().startswith("EVIDENCE:"):
            try:
                raw = line.split(":", 1)[-1].strip()
                num = "".join(c for c in (raw.split()[0] if raw.split() else "") if c in "0123456789.")
                if num:
                    result["evidence"] = max(0, min(10, float(num)))
            except Exception:
                pass

        elif line.strip().upper().startswith("PERSUASIVE:"):
            try:
                raw = line.split(":", 1)[-1].strip()
                num = "".join(c for c in (raw.split()[0] if raw.split() else "") if c in "0123456789.")
                if num:
                    result["persuasive"] = max(0, min(10, float(num)))
            except Exception:
                pass

        elif line.startswith("CLAIMS:"):
            raw = line.replace("CLAIMS:", "").strip()
            result["claims"] = [i.strip() for i in raw.split(",") if i.strip()]

        elif line.startswith("INDICATORS:"):
            raw = line.replace("INDICATORS:", "").strip()
            result["indicators"] = [i.strip() for i in raw.split(",") if i.strip()]

        elif line.strip().upper().startswith("REASONS:"):
            raw = line.split(":", 1)[-1].strip()
            result["reasons"] = [i.strip() for i in raw.split("|") if i.strip()]

        elif line.startswith("SUMMARY:"):
            result["summary"] = line.replace("SUMMARY:", "").strip()

    return result


def parse_response_group(text: str) -> dict:

    result = {
        "verdict": "",
        "summary": ""
    }

    for line in text.strip().splitlines():

        if line.startswith("VERDICT:"):
            result["verdict"] = line.replace("VERDICT:", "").strip()

        elif line.startswith("SUMMARY:"):
            result["summary"] = line.replace("SUMMARY:", "").strip()

    return result

def analyze_all_articles(articles: list) -> list:
    semaphore = asyncio.Semaphore(GROQ_MAX_CONCURRENT)

    async def run():
        client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        try:
            tasks = [_analyze_bias_one(article, semaphore, client) for article in articles]
            return await asyncio.gather(*tasks)
        finally:
            # Close the underlying httpx client while the event loop is still running
            # to avoid "Event loop is closed" when asyncio.run() tears down the loop
            for attr in ("_client", "_http_client", "client"):
                if hasattr(client, attr):
                    c = getattr(client, attr)
                    if hasattr(c, "aclose"):
                        try:
                            await c.aclose()
                        except Exception:
                            pass
                        break

    return asyncio.run(run())

def compute_verdict_from_scores(articles: list) -> dict:
    """
    Compute verdict and summary from per-article bias scores (no LLM).
    Score range 0 (no bias) to 10 (heavily biased); we use the average score.
    """
    if not articles:
        return {"verdict": "no bias", "summary": "No articles to analyze."}
    scores = []
    for a in articles:
        s = (a.get("bias") or {}).get("score")
        if s is not None:
            try:
                scores.append(max(0, min(10, float(s))))
            except (TypeError, ValueError):
                pass
    if not scores:
        return {"verdict": "unknown", "summary": "No bias scores available."}
    avg = sum(scores) / len(scores)
    if avg < 2:
        verdict = "no bias"
    elif avg < 4:
        verdict = "low bias"
    elif avg < 6:
        verdict = "moderate bias"
    else:
        verdict = "high bias"
    n = len(articles)
    summary = f"<short summary of the user query based on findings or how likely the query is bias or very distorted>"
    return {"verdict": verdict, "summary": summary}


def get_comparative_framings(articles: list) -> list:
    """
    For each article, get a short (3–6 word) framing phrase that contrasts with the others
    (e.g. safety focus vs conflict angle vs sport impact).
    """
    if not articles:
        return []
    articles_desc = []
    for i, a in enumerate(articles):
        summary = (a.get("bias") or {}).get("summary", "") or ""
        articles_desc.append(
            f"[{i + 1}] Source: {a.get('source', 'Unknown')}\nTitle: {a.get('title', '')}\nSummary: {summary}"
        )
    prompt = f"""You are comparing how different news sources frame the same story.

Articles (in order):
---
{chr(10).join(articles_desc)}
---

For each article, give ONE short framing phrase (3–6 words) that captures how THIS article frames the story compared to the others. Use contrasting angles, e.g.:
- safety/risk focus
- conflict or regional tension
- tragedy or human cost
- sport/event impact
- leadership or institutional decision
- blame or responsibility

Return exactly one line per article, in the same order (article 1, then 2, ...). Each line must start with FRAMING:
FRAMING: <phrase for article 1>
FRAMING: <phrase for article 2>
...
"""

    last_error = None
    for attempt in range(GROQ_MAX_RETRIES):
        try:
            response = Groq(api_key=os.getenv("GROQ_API_KEY")).chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.choices[0].message.content or ""
            framings = []
            for line in text.strip().splitlines():
                line = line.strip()
                if line.upper().startswith("FRAMING:"):
                    phrase = line.split(":", 1)[-1].strip()
                    if phrase:
                        framings.append(phrase)
            while len(framings) < len(articles):
                framings.append("—")
            return framings[: len(articles)]
        except Exception as e:
            last_error = e
            if _is_rate_limit_error(e) and attempt < GROQ_MAX_RETRIES - 1:
                wait = _retry_after(e) * (2 ** attempt)
                print(f"Rate limit (framings), retrying in {wait:.0f}s...")
                time.sleep(wait)
            else:
                break
    print(f"Comparative framings error: {last_error}")
    return [""] * len(articles)


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
    print(f"Running analysis for google news... starting at ", datetime.datetime.now().time().strftime("%H:%M:%S"))
    articles = analyze_all_articles(articles)
    print(f"[✓] Running analysis for google news... finished at ", datetime.datetime.now().time().strftime("%H:%M:%S"))

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

    print(f"Running analysis for newsapi... finished at ", datetime.datetime.now().time().strftime("%H:%M:%S"))
    articles = analyze_all_articles(articles)

    print(f"[✓] Running analysis for newsapi... finished at ", datetime.datetime.now().time().strftime("%H:%M:%S"))
    return articles



# ----------------------------
# COMBINE + CACHE
# ----------------------------
# #region agent log
def _debug_log(data: dict):
    import json
    try:
        with open("/Users/georgetong/PycharmProjects/BiasCheck/.cursor/debug-7140ec.log", "a") as f:
            f.write(json.dumps({"sessionId": "7140ec", **data, "timestamp": datetime.datetime.now().timestamp() * 1000}) + "\n")
    except Exception:
        pass
# #endregion

@lru_cache(maxsize=50)
def get_related_news(topic):

    google_articles = get_google_news(topic)
    api_articles = get_newsapi_news(topic)
    # #region agent log
    _debug_log({"location": "services.py:get_related_news", "message": "after feeds", "data": {"len_google": len(google_articles), "len_api": len(api_articles), "hypothesisId": "A"}})
    # #endregion

    combined = google_articles + api_articles

    # Drop articles the LLM marked as unanalyzable (paywall, JS-only, no content, etc.)
    combined = [a for a in combined if (a.get("bias") or {}).get("analyzable", True)]

    # Verdict from quantitative bias scores (no extra LLM call)
    group_summary = compute_verdict_from_scores(combined)

    seen = set()
    unique_articles = []

    for article in combined:
        # Dedupe by title + source so same headline from different outlets each get plotted
        key = (article["title"].lower(), (article.get("source") or "").strip())

        if key not in seen:
            unique_articles.append(article)
            seen.add(key)

    # #region agent log
    _debug_log({"location": "services.py:get_related_news", "message": "after dedup", "data": {"len_combined": len(combined), "len_unique": len(unique_articles), "sources": [a.get("source") for a in unique_articles], "hypothesisId": "B"}})
    # #endregion

    # Short comparative framing phrases (e.g. safety focus vs conflict angle)
    framings = get_comparative_framings(unique_articles)
    for i, article in enumerate(unique_articles):
        article["key_framing"] = framings[i] if i < len(framings) else "—"

    # #region agent log
    _debug_log({"location": "services.py:get_related_news", "message": "bias scores for chart", "data": {"scores": [{"source": a.get("source"), "evidence": (a.get("bias") or {}).get("evidence"), "persuasive": (a.get("bias") or {}).get("persuasive")} for a in unique_articles], "hypothesisId": "F"}})
    # #endregion

    results = []
    results.append(unique_articles)
    results.append(group_summary)

    return results
