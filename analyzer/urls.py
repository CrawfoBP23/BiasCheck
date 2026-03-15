from django.urls import path
from .views import home, search_news, analyze_article

urlpatterns = [
    path('', home),
    path('api/search/', search_news),
    path('api/analyze/', analyze_article),
]
