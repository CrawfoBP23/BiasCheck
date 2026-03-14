from django.http import JsonResponse
import requests
from django.shortcuts import render


def home(request):
    return render(request, "index.html")


def analyze_article(request):

    url = request.GET.get("url")

    if not url:
        return JsonResponse({"error": "Missing URL parameter"})

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

