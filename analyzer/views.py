from django.http import JsonResponse
from django.shortcuts import render
from .services import get_related_news, analyze_bias


def home(request):
    return render(request, "index.html")


def search_news(request):

    topic = request.GET.get("topic")

    if not topic:
        return JsonResponse([])

    articles = get_related_news(topic)

    return JsonResponse(articles, safe=False)


def analyze_article(request):

    title = request.GET.get("title")
    summary = request.GET.get("summary")
    url = request.GET.get("url")

    article = {
        "title": title,
        "summary": summary,
        "url": url
    }

    result = analyze_bias(article)

    return JsonResponse(result["bias"])
