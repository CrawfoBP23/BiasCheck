from django.urls import path
from .views import analyze_article, home

urlpatterns = [
    path('analyze/', analyze_article),
    path("", home)
]
