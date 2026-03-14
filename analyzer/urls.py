from django.urls import path
from .views import analyze_article

urlpatterns = [
    path('analyze/', analyze_article),
]
