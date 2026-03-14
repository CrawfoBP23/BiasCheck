from django.http import JsonResponse
import requests
from dotenv import load_dotenv
import os

load_dotenv()

def analyze_article(request):

    params = {
        'q': query,
        'apiKey': os.getenv('NEWS_API_KEY'),
        'pageSize': 10,
        'language': 'en',
        'sortBy': 'publishedAt',
    }

    url = request.GET.get("https://newsapi.org/v2/everything", params=params)
    query = "Cats need milk"

    if not url:
        return JsonResponse({"error": "Missing URL parameter"})
    
    data = url.json()

    bias_words = [
        "outrageous",
        "disastrous",
        "shocking",
        "radical"
    ]

    try:
        text = requests.get(url).text.lower()
    except:
        return JsonResponse({"error": "Could not fetch article"})

    score = sum(word in text for word in bias_words)

    return JsonResponse({
        "bias_score": score,
        "message": "Moderate bias detected" if score > 2 else "Low bias"
    })
