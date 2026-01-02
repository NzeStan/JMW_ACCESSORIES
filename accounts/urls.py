from django.urls import path
from .views import GoogleLogin, GithubLogin

urlpatterns = [
    path("google/", GoogleLogin.as_view(), name="google_login"),
    path("github/", GithubLogin.as_view(), name="github_login"),
]
