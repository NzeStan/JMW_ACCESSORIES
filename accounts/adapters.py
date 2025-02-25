from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        """Allow or restrict signup."""
        return True  # Keep signup open


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """Link Google login to existing account instead of failing."""
        user = sociallogin.user
        if user.email:
            existing_users = User.objects.filter(email=user.email)
            if existing_users.exists():
                existing_user = existing_users.first()  # Take the first user found
                sociallogin.connect(request, existing_user)  # Link Google login
                sociallogin.state["process"] = "connect"
                # Ensure the email is marked as verified
                existing_user.emailaddress_set.update(verified=True)
                return  # Stop further processing

        # Ensure the username is set properly
        if not user.pk:  # If the user is not yet saved
            if not user.username:  # Generate a username if missing
                base_username = slugify(user.email.split("@")[0])
                new_username = base_username
                count = 1
                while User.objects.filter(username=new_username).exists():
                    new_username = f"{base_username}-{count}"
                    count += 1
                user.username = new_username
            user.save()

    def save_user(self, request, sociallogin, form=None):
        """Save the user and mark their email as verified for social accounts."""
        user = super().save_user(request, sociallogin, form)
        # Mark email as verified for social accounts
        user.emailaddress_set.update(verified=True, primary=True)
        return user
