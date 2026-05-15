import os
import sys
from datetime import timedelta
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from corsheaders.defaults import default_headers, default_methods


try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from: {env_path}")
    elif os.getenv("DEBUG", "false").lower() == "true":
        # Only show the warning in development/debug mode
        print(f" .env file not found at: {env_path}")
except Exception as e:
    if os.getenv("DEBUG", "false").lower() == "true":
        print(f" Error loading .env: {e}")

BASE_DIR = Path(__file__).resolve().parent.parent

TESTING = 'test' in sys.argv or 'pytest' in sys.argv

# -----------------------------
# Core Config
# -----------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,django-msvx.onrender.com,django-jrl5.onrender.com,django-8dru.onrender.com,django-six-gamma.vercel.app"
).replace(" ", "").split(",")

# Allow all Render and Vercel subdomains so preview branches work automatically
ALLOWED_HOSTS.append(".onrender.com")
ALLOWED_HOSTS.append(".vercel.app")

if os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.getenv("RENDER_EXTERNAL_HOSTNAME"))

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# -----------------------------
# Installed Apps
# -----------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'cloudinary_storage',
    'cloudinary',
    'accounts',
    'lead_magnets',
]

# -----------------------------
# Middleware
# -----------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_project.middleware.CatchAllMiddleware',
]

ROOT_URLCONF = 'django_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'django_project.wsgi.application'

# -----------------------------
# Database
# -----------------------------
import dj_database_url

DATABASE_URL = (
    os.getenv("SUPABASE_DATABASE_URL")
    or os.getenv("SUPABASE_STRING")
    or os.getenv("DATABASE_URL")
)

if DATABASE_URL:
    # 🚀 SUPABASE POOLER FIX:
    # If using Supabase pooler (pooler.supabase.com) and username is just 'postgres',
    # we need to append the project ref to the username: 'postgres.PROJECT_REF'
    # We try to find PROJECT_REF in env vars if it's not in the URL.
    project_ref = os.getenv("SUPABASE_PROJECT_REF") or os.getenv("SUPABASE_PROJECT_ID")
    if project_ref and "pooler.supabase.com" in DATABASE_URL and "postgres:" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("postgres:", f"postgres.{project_ref}:")
        print(f"🔧 Auto-patched DATABASE_URL with project ref: {project_ref}")

    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }
    if 'OPTIONS' not in DATABASES['default']:
        DATABASES['default']['OPTIONS'] = {}
    DATABASES['default']['OPTIONS']['sslmode'] = os.getenv("POSTGRES_SSLMODE", "require")
    
    # Extra diagnostic for Supabase errors
    db_host = DATABASES['default'].get('HOST', '')
    db_user = DATABASES['default'].get('USER', '')
    if "pooler.supabase.com" in db_host and "." not in db_user:
        print("⚠️ WARNING: You are connecting to Supabase Pooler but your username does not contain a project reference.")
        print("⚠️ This will likely cause 'FATAL: Tenant or user not found'.")
        print("⚠️ Fix: Change your username to 'postgres.YOUR_PROJECT_REF' in the connection string.")
else:
    POSTGRES_DB       = os.getenv("POSTGRES_DB")
    POSTGRES_USER     = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_HOST     = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT     = os.getenv("POSTGRES_PORT", "5432")

    if all([POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST]):
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': POSTGRES_DB,
                'USER': POSTGRES_USER,
                'PASSWORD': POSTGRES_PASSWORD,
                'HOST': POSTGRES_HOST,
                'PORT': POSTGRES_PORT,
                'CONN_MAX_AGE': 0 if TESTING else 600,
                'OPTIONS': {
                    'sslmode': os.getenv("POSTGRES_SSLMODE", "require"),
                },
            }
        }
    else:
        print("No PostgreSQL configuration found.")
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }

default_db = DATABASES.get('default', {})
print(f"DB backend: {default_db.get('ENGINE', '')}")
if default_db.get('ENGINE') == 'django.db.backends.postgresql':
    print(f"DB host: {default_db.get('HOST', '')}")
else:
    print(f"DB name: {default_db.get('NAME', '')}")

# -----------------------------
# Password Validation
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# -----------------------------
# Static & Media
# -----------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        # CompressedStaticFilesStorage (not Manifest) — avoids ValueError when
        # staticfiles.json is missing or stale after a fresh deploy.
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -----------------------------
# Cloudinary
# -----------------------------
CLOUDINARY_STORAGE = {
    'CLOUD_NAME':    os.getenv("CLOUDINARY_CLOUD_NAME"),
    'API_KEY':       os.getenv("CLOUDINARY_API_KEY"),
    'API_SECRET':    os.getenv("CLOUDINARY_API_SECRET"),
    'RESOURCE_TYPES': ['image', 'video', 'raw'],
}

# -----------------------------
# Authentication
# -----------------------------
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'django_project.exceptions.custom_exception_handler',
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":    timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME":   timedelta(days=1),
    "ROTATE_REFRESH_TOKENS":    False,
    "BLACKLIST_AFTER_ROTATION": False,
}

# -----------------------------
# CORS + CSRF
# -----------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://django-six-gamma.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True

# Also keep regexes for safety in some environments
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://django-.*\.vercel\.app$",
    r"^https://django-.*-kash4511s-projects\.vercel\.app$",
]

CORS_URLS_REGEX = r'^/api/.*$'


# Optional but helps with some older browsers
CORS_PREFLIGHT_MAX_AGE = 86400

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-requested-with",
    "content-type",
    "accept",
    "origin",
    "authorization",
    "x-csrftoken",
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CSRF_TRUSTED_ORIGINS = [
    "https://django-six-gamma.vercel.app",
    "https://django-4muchbxg6-kash4511s-projects.vercel.app",
    "https://django-git-kaashifs-branch-kash4511s-projects.vercel.app",
    "https://django-msvx.onrender.com",
    "https://django-jrl5.onrender.com",
    "https://*.vercel.app",
    "https://*.onrender.com",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"