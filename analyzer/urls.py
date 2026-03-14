from django.urls import path
from .views import home, search_news, analyze_article

urlpatterns = [
    path('', home),
    path('search/', search_news),
    path('analyze/', analyze_article),
]
