from django.urls import path, include
from .views import (
    GoogleLogin, GithubLogin, CustomLoginView, CustomLogoutView,
    CustomPasswordResetView, PasswordResetConfirmView, CustomUserDetailsView
)
from dj_rest_auth.registration.views import RegisterView
from dj_rest_auth.views import PasswordChangeView
from .serializers import ChangePasswordSerializer
from rest_framework import status
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)


class CustomPasswordChangeView(PasswordChangeView):
    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password changed successfully"},
            status=status.HTTP_200_OK
        )


urlpatterns = [
    # Registration & Login
    path('register/', RegisterView.as_view(), name='rest_register'),
    path('login/', CustomLoginView.as_view(), name='rest_login'),
    path('logout/', CustomLogoutView.as_view(), name='rest_logout'),
    
    # Password Management
    path('password/reset/', CustomPasswordResetView.as_view(), name='rest_password_reset'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='rest_password_reset_confirm'),
    path('password/change/', CustomPasswordChangeView.as_view(), name='rest_password_change'),
    
    # User Details
    path('user/', CustomUserDetailsView.as_view(), name='rest_user_details'),
    
    # Social Authentication
    path('google/', GoogleLogin.as_view(), name='google_login'),
    path('github/', GithubLogin.as_view(), name='github_login'),
    
    # Email Verification (if using dj-rest-auth for email)
    path('registration/', include('dj_rest_auth.registration.urls')),
]

# Include allauth URLs for email verification
urlpatterns += [
    path('verify-email/', include('allauth.urls')),
]