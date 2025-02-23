from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        """Allow or restrict signup."""
        return True  # Keep signup open


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        """Allow users to sign up via social authentication."""
        return True

    def pre_social_login(self, request, sociallogin):
        """Ensure social logins don't require email verification."""
        user = sociallogin.user
        if user.email and not user.emailaddress_set.filter(email=user.email).exists():
            # Auto-verify the email for social accounts
            user.emailaddress_set.create(email=user.email, verified=True, primary=True)
