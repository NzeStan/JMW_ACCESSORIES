from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from dj_rest_auth.views import (
    LoginView, LogoutView, PasswordChangeView, 
    PasswordResetView, PasswordResetConfirmView, UserDetailsView
)
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.SOCIAL_AUTH_CALLBACK_URL
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            logger.info(f"Google OAuth login successful for user")
            return response
        except Exception as e:
            logger.error(f"Google OAuth login failed: {str(e)}")
            return Response(
                {"detail": "Google authentication failed"},
                status=status.HTTP_400_BAD_REQUEST
            )


class GithubLogin(SocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    callback_url = settings.SOCIAL_AUTH_CALLBACK_URL
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            logger.info(f"GitHub OAuth login successful for user")
            return response
        except Exception as e:
            logger.error(f"GitHub OAuth login failed: {str(e)}")
            return Response(
                {"detail": "GitHub authentication failed"},
                status=status.HTTP_400_BAD_REQUEST
            )


class CustomLoginView(LoginView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            logger.info(f"User logged in successfully: {request.data.get('email')}")
        return response


class CustomLogoutView(LogoutView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logger.info(f"User logging out: {request.user.email}")
        response = super().post(request, *args, **kwargs)
        # Clear any custom cookies if needed
        return response


class CustomPasswordResetView(PasswordResetView):
    def post(self, request, *args, **kwargs):
        logger.info(f"Password reset requested for: {request.data.get('email')}")
        return super().post(request, *args, **kwargs)


class CustomUserDetailsView(UserDetailsView):
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        """Update user details"""
        return self.partial_update(request, *args, **kwargs)