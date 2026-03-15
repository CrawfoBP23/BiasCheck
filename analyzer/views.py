from django.http import JsonResponse
from django.shortcuts import render
from .services import get_related_news
import time

def home(request):
    return render(request, "index.html")


def search_news(request):

    topic = request.GET.get("topic")

    if not topic:
        return JsonResponse({"articles": []})

    start = time.time()

    results = get_related_news(topic)
    articles = results[0]
    group_summary = results[1]

    elapsed = round(time.time() - start, 2)

    return JsonResponse({
        "articles": articles,
        "group_summary": group_summary,
        "elapsed": elapsed
    })


def analyze_article(request):
    return JsonResponse({
        "message": "Article analysis not implemented yet"
    })
