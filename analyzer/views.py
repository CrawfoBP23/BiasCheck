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

    try:
        results = get_related_news(topic)
        articles = results[0]
        group_summary = results[1]
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        # Surface Groq / analysis errors to the UI instead of hanging
        return JsonResponse(
            {
                "error": "News bias analysis failed. This can happen if the AI backend (Groq) is unavailable or your API credits are exhausted.",
                "details": str(e),
                "elapsed": elapsed,
            },
            status=500,
        )

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
