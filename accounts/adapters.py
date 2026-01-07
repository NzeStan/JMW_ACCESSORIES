from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging
from rest_framework import serializers

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        """Allow or restrict signup."""
        return True
    
    def send_mail(self, template_prefix, email, context):
        """Custom email sending with HTML support."""
        subject = render_to_string(f'{template_prefix}_subject.txt', context)
        subject = "".join(subject.splitlines())
        
        html_message = render_to_string(f'{template_prefix}_message.html', context)
        plain_message = strip_tags(html_message)
        
        from_email = self.get_from_email()
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email sent to {email} with subject: {subject}")
    
    def save_user(self, request, user, form, commit=True):
        """Save user with additional fields."""
        user = super().save_user(request, user, form, commit=False)
        
        # Add any custom fields
        if commit:
            user.save()
        
        # Send welcome email
        if settings.ACCOUNT_EMAIL_VERIFICATION != "mandatory" or user.emailaddress_set.filter(verified=True).exists():
            self.send_welcome_email(user)
        
        return user
    
    def send_welcome_email(self, user):
        """Send welcome email to new users."""
        context = {
            'user': user,
            'site_name': 'JUME MEGA WEARS',
            'login_url': settings.FRONTEND_LOGIN_URL if hasattr(settings, 'FRONTEND_LOGIN_URL') else '/login',
        }
        
        self.send_mail('account/email/welcome', user.email, context)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """Link social login to existing account instead of failing."""
        user = sociallogin.user
        
        if user.email:
            existing_users = User.objects.filter(email=user.email)
            if existing_users.exists():
                existing_user = existing_users.first()
                
                # Don't link if the existing user has a password (normal account)
                # unless explicitly requested
                if existing_user.has_usable_password():
                    # You might want to ask for confirmation here
                    # For now, we'll link automatically
                    pass
                
                sociallogin.connect(request, existing_user)
                sociallogin.state["process"] = "connect"
                
                # Ensure the email is marked as verified
                email_address = existing_user.emailaddress_set.filter(email=user.email).first()
                if email_address:
                    email_address.verified = True
                    email_address.primary = True
                    email_address.save()
                
                logger.info(f"Social account linked to existing user: {user.email}")
                return
        
        # Generate username if missing
        if not user.pk and not user.username:
            base_username = slugify(user.email.split("@")[0])
            new_username = base_username
            count = 1
            while User.objects.filter(username=new_username).exists():
                new_username = f"{base_username}-{count}"
                count += 1
            user.username = new_username
    
    def save_user(self, request, sociallogin, form=None):
        """Save the user and mark their email as verified for social accounts."""
        user = super().save_user(request, sociallogin, form)
        
        # Mark email as verified for social accounts
        email_address = user.emailaddress_set.filter(email=user.email).first()
        if email_address:
            email_address.verified = True
            email_address.primary = True
            email_address.save()
        
        # Send welcome email for social signups
        if hasattr(self, 'send_welcome_email'):
            self.send_welcome_email(user)
        
        logger.info(f"Social account created for user: {user.email}")
        return user
    
    def is_auto_signup_allowed(self, request, sociallogin):
        """Allow auto signup for social accounts."""
        return True
    
    def validate_disconnect(self, account, accounts):
        """Prevent disconnection of last social account if no password set."""
        user = account.user
        if not user.has_usable_password() and accounts.count() == 1:
            raise serializers.ValidationError(
                "Cannot disconnect last social account without setting a password"
            )