"""Local-first settings. Production requires an explicit secret and HTTPS setup."""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() in {"true", "1", "yes"}
DATA_DIR = Path(os.environ.get("GEMCRM_DATA_DIR", BASE_DIR / ".data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Set DJANGO_SECRET_KEY when DJANGO_DEBUG=false.")
    # A private, ignored local file keeps development sessions valid on restart.
    secret_path = DATA_DIR / "development-secret-key"
    try:
        with open(secret_path, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
            stream.write(get_random_secret_key())
    except FileExistsError:
        pass
    SECRET_KEY = secret_path.read_text().strip()

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
    if host.strip()
]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crm",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "gemcrm.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "gemcrm.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": DATA_DIR / "db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "pt-br"
TIME_ZONE = os.environ.get("GEMCRM_TIME_ZONE", "America/Sao_Paulo")
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = DATA_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "crm:dashboard"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
