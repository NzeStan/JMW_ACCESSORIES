"""
Django settings for jmw project - API ONLY ARCHITECTURE

This is a cleaned version with all template/frontend elements removed.
Only contains what's needed for a REST API backend.
"""

from pathlib import Path
from environs import Env
import os

env = Env()
env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# SECURITY
# ==============================================================================

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)

if not DEBUG:
    ALLOWED_HOSTS = [
        "jmw-accessories.onrender.com",
        "www.jumemegawears.com",
        "jumemegawears.com",
    ]
    CSRF_TRUSTED_ORIGINS = [
        "https://jmw-accessories.onrender.com",
        "https://www.jumemegawears.com",
        "https://jumemegawears.com",
    ]
else:
    ALLOWED_HOSTS = [
        "localhost",
        "127.0.0.1",
        ".ngrok-free.app",          
    ]
    CSRF_TRUSTED_ORIGINS = ["https://*.ngrok-free.app"]
    

# ==============================================================================
# APPLICATIONS
# ==============================================================================

INSTALLED_APPS = [
    # Django core (minimal for API)
    "django.contrib.admin",  # Keep for admin panel
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",  # ← ADDED: Required for admin login and allauth
    "django.contrib.messages",  # Needed for admin
    "django.contrib.staticfiles",  # Needed for admin static files
    "django.contrib.sites",  # Required by allauth
    
    # REST Framework & Auth
    "rest_framework",
    "rest_framework.authtoken",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    
    # Social Authentication
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.github",
    
    # Third-party utilities
    "django_filters",  # ← ADDED: For DRF filtering (DjangoFilterBackend)
    "whitenoise.runserver_nostatic",
    'background_task',
    
    # Local apps
    "accounts.apps.AccountsConfig",
    "products.apps.ProductsConfig",
    "cart.apps.CartConfig",
    "measurement.apps.MeasurementConfig",
    "feed.apps.FeedConfig",
    "order.apps.OrderConfig",
    "payment.apps.PaymentConfig",
    "bulk_orders.apps.BulkOrdersConfig",
    "webhook_router.apps.WebhookRouterConfig",
    "orderitem_generation.apps.OrderitemGenerationConfig",
]

# Add debug toolbar only in development
if DEBUG:
    INSTALLED_APPS.append("debug_toolbar")

# ==============================================================================
# MIDDLEWARE
# ==============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

if DEBUG:
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")

# ==============================================================================
# URLS & WSGI
# ==============================================================================

ROOT_URLCONF = "jmw.urls"
WSGI_APPLICATION = "jmw.wsgi.application"

# ==============================================================================
# TEMPLATES (Minimal - Only for Admin & PDF Generation)
# ==============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],  # No custom template directories needed
        "APP_DIRS": True,  # Keep for admin templates and app-specific templates
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ==============================================================================
# DATABASE
# ==============================================================================

DATABASES = {
    "default": env.dj_db_url("DATABASE_URL", default="postgres://postgres@db/postgres")
}

# ==============================================================================
# AUTHENTICATION & PASSWORDS
# ==============================================================================

AUTH_USER_MODEL = "accounts.CustomUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

# ==============================================================================
# DJANGO-ALLAUTH CONFIGURATION
# ==============================================================================

SITE_ID = 1

# Account settings
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "optional" #"mandatory"

# Social account settings
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_USERNAME_REQUIRED = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_AVATAR_SUPPORT = False

# Provider specific settings
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": env("GOOGLE_CLIENT_ID"),
            "secret": env("GOOGLE_SECRET"),
        },
        "SCOPE": ["profile", "email"],
    },
    "github": {
        "APP": {
            "client_id": env("GITHUB_CLIENT_ID"),
            "secret": env("GITHUB_SECRET"),
        },
        "SCOPE": ["read:user", "user:email"],
    },
}

# ==============================================================================
# REST FRAMEWORK & JWT
# ==============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE": "jmw-auth",
    "JWT_AUTH_REFRESH_COOKIE": "jmw-refresh-token",
    "USER_DETAILS_SERIALIZER": "accounts.serializers.CustomUserSerializer",
    "REGISTER_SERIALIZER": "accounts.serializers.CustomRegisterSerializer",
}

# ==============================================================================
# INTERNATIONALIZATION
# ==============================================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

# ==============================================================================
# STATIC FILES (Only for Django Admin)
# ==============================================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

if DEBUG:
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
    WHITENOISE_AUTOREFRESH = False
    WHITENOISE_USE_FINDERS = True
    WHITENOISE_MANIFEST_STRICT = False

# ==============================================================================
# MEDIA FILES & CLOUDINARY
# ==============================================================================

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Cloudinary configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': env('CLOUDINARY_API_KEY'),
    'API_SECRET': env('CLOUDINARY_API_SECRET'),
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# ==============================================================================
# EMAIL CONFIGURATION
# ==============================================================================

if DEBUG:
    EMAIL_FILE_PATH = str(BASE_DIR / "sent_emails")
    EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.zoho.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = "ifeanyinnamani@jumemegawears.com"
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = "JMW <info@jumemegawears.com>"
CONTACT_EMAIL = "contact@jumemegawears.com"

# Admin notification
ADMINS = [("Ifeanyi Nnamani", "ifeanyinnamani@jumemegawears.com")]
SERVER_EMAIL = "server@jumemegawears.com"

# ==============================================================================
# BACKGROUND TASKS
# ==============================================================================
BACKGROUND_TASK_RUN_ASYNC = True
BACKGROUND_TASK_ASYNC_THREADS = 4

# ==============================================================================
# CACHING
# ==============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "my_cache_table",
    }
}

# ==============================================================================
# EXTERNAL API KEYS
# ==============================================================================

# YouTube API
YOUTUBE_API_KEY = env.str("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = env.str("YOUTUBE_CHANNEL_ID")

# Paystack Payment Gateway
if DEBUG:
    PAYSTACK_TEST_SECRET_KEY = env("PAYSTACK_TEST_SECRET_KEY")
    PAYSTACK_TEST_PUBLIC_KEY = env("PAYSTACK_TEST_PUBLIC_KEY")
else:
    PAYSTACK_LIVE_SECRET_KEY = env("PAYSTACK_LIVE_SECRET_KEY")
    PAYSTACK_LIVE_PUBLIC_KEY = env("PAYSTACK_LIVE_PUBLIC_KEY")

# ==============================================================================
# COMPANY DETAILS (For Receipts/PDFs)
# ==============================================================================
COMPANY_NAME = "JUME MEGA WEARS & ACCESSORIES"
COMPANY_ADDRESS = "16 Emejiaka Street, Ngwa Rd, Aba Abia State"
COMPANY_PHONE = "+2348139425458"
COMPANY_EMAIL = "info@jumemegawears.com"

# ==============================================================================
# LOGGING
# ==============================================================================

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
os.chmod(LOGS_DIR, 0o755)

LOG_FILES = ["debug.log", "info.log", "error.log", "critical.log", "daily.log"]
for log_file in LOG_FILES:
    log_path = LOGS_DIR / log_file
    if not log_path.exists():
        log_path.touch()
    os.chmod(log_path, 0o644)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "detailed": {
            "format": "{levelname} {asctime} {name} {module} {funcName} {lineno} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG" if DEBUG else "INFO",
            "filters": ["require_debug_true"] if DEBUG else ["require_debug_false"],
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file_debug": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "debug.log"),
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 10,
            "formatter": "detailed",
        },
        "file_info": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "info.log"),
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "file_error": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "error.log"),
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 10,
            "formatter": "detailed",
        },
        "critical_errors": {
            "level": "CRITICAL",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "critical.log"),
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 30,
            "formatter": "detailed",
        },
        "timed_rotating_file": {
            "level": "INFO",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOGS_DIR / "daily.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
            "formatter": "detailed",
            "include_html": True,
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console", "file_info", "file_error", "timed_rotating_file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": True,
        },
        "django": {
            "handlers": ["console", "file_info", "mail_admins"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["file_error", "mail_admins", "critical_errors"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["file_error", "mail_admins", "critical_errors"],
            "level": "ERROR",
            "propagate": False,
        },
        # App-specific loggers
        "accounts": {
            "handlers": ["console", "file_debug", "file_info", "file_error"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "products": {
            "handlers": ["console", "file_debug", "file_info", "file_error"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "cart": {
            "handlers": ["console", "file_debug", "file_info", "file_error"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "order": {
            "handlers": ["console", "file_debug", "file_info", "file_error"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "payment": {
            "handlers": ["console", "file_debug", "file_info", "file_error"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "bulk_orders": {
            "handlers": ["console", "file_debug", "file_info", "file_error"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "feed": {
            "handlers": ["console", "file_debug", "file_info", "file_error"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "measurement": {
            "handlers": ["console", "file_debug", "file_info", "file_error"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# ==============================================================================
# DJANGO DEBUG TOOLBAR (Development Only)
# ==============================================================================

if DEBUG:
    import socket
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[:-1] + "1" for ip in ips]

# ==============================================================================
# PRODUCTION SECURITY
# ==============================================================================

if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=2592000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
    SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
    SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=True)
    CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ==============================================================================
# MISC
# ==============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"