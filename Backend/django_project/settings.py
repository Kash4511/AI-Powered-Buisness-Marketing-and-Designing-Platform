import os
from datetime import timedelta
from pathlib import Path
from corsheaders.defaults import default_headers, default_methods

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from: {env_path}")
    else:
        print(f"⚠️  .env file not found at: {env_path}")
except Exception as e:
    print(f"⚠️ Error loading .env: {e}")

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------
# Core Config
# -----------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# IMPORTANT: Render does NOT read .env unless added in dashboard
# Make sure ALLOWED_HOSTS is set in Render environment settings
ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,django-msvx.onrender.com,django-six-gamma.vercel.app"
).split(",")

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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_project.middleware.CatchAllMiddleware',
]

ROOT_URLCONF = 'django_project.urls'

# -----------------------------
# Templates
# -----------------------------
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
# Defaults to SQLite for local development. If Postgres env vars are present,
# configures Postgres (compatible with Supabase).
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_SSLMODE = os.getenv("POSTGRES_SSLMODE", "require")
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SUPERBASE_STRING")

if all([POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST]):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': POSTGRES_DB,
            'USER': POSTGRES_USER,
            'PASSWORD': POSTGRES_PASSWORD,
            'HOST': POSTGRES_HOST,
            'PORT': POSTGRES_PORT,
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'sslmode': POSTGRES_SSLMODE,
            },
        }
    }
elif DATABASE_URL and DATABASE_URL.startswith(('postgres://', 'postgresql://')):
    # Minimal parser for DATABASE_URL if provided
    # Example: postgresql://user:pass@host:5432/dbname?sslmode=require
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(DATABASE_URL)
        qs = parse_qs(parsed.query)
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': parsed.path.lstrip('/'),
                'USER': parsed.username or '',
                'PASSWORD': parsed.password or '',
                'HOST': parsed.hostname or '',
                'PORT': str(parsed.port or '5432'),
                'CONN_MAX_AGE': 600,
                'OPTIONS': {
                    'sslmode': (qs.get('sslmode', ['require'])[0]),
                },
            }
        }
    except Exception:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

default_db = DATABASES.get('default', {})
print(f"🔌 DB backend: {default_db.get('ENGINE', '')}")
print(f"🔌 DB name: {default_db.get('NAME', '')}")

# -----------------------------
# Password Validation
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -----------------------------
# Internationalization
# -----------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# -----------------------------
# Static & Media
# -----------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -----------------------------
# Cloudinary
# -----------------------------
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv("CLOUDINARY_CLOUD_NAME"),
    'API_KEY': os.getenv("CLOUDINARY_API_KEY"),
    'API_SECRET': os.getenv("CLOUDINARY_API_SECRET"),
}
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

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
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
}

# -----------------------------
# CORS + CSRF
# -----------------------------
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "https://django-six-gamma.vercel.app",
    "https://django-4muchbxg6-kash4511s-projects.vercel.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CORS_URLS_REGEX = r'^/api/.*$'

CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_HEADERS = ["*"]

CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

CSRF_TRUSTED_ORIGINS = [
    "https://django-six-gamma.vercel.app",
    "https://django-msvx.onrender.com",
]

# -----------------------------
# Auto Field
# -----------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
