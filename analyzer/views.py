from django.http import JsonResponse
from django.shortcuts import render
from .services import get_related_news


def home(request):
    return render(request, "index.html")


def search_news(request):

    topic = request.GET.get("topic")

    if not topic:
        return JsonResponse({"articles": []})

    articles = get_related_news(topic)

    return JsonResponse({
        "articles": articles
    })


def analyze_article(request):
    return JsonResponse({
        "message": "Article analysis not implemented yet"
    })
