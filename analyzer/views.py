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

    # #region agent log
    try:
        with open("/Users/georgetong/PycharmProjects/BiasCheck/.cursor/debug-7140ec.log", "a") as f:
            import json
            f.write(json.dumps({"sessionId": "7140ec", "location": "views.py:search_news", "message": "before JsonResponse", "data": {"len_articles": len(articles)}, "timestamp": time.time() * 1000, "hypothesisId": "C"}) + "\n")
    except Exception:
        pass
    # #endregion

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
