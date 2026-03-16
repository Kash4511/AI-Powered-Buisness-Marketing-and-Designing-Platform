import os
import sys
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

# Detect if we are running tests
TESTING = 'test' in sys.argv or 'pytest' in sys.argv

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
).replace(" ", "").split(",")

# Allow all Render subdomains for flexibility
ALLOWED_HOSTS.append(".onrender.com")

# Ensure Render's own health-check domain is allowed if needed (though usually handled by Render)
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
    'whitenoise.middleware.WhiteNoiseMiddleware', # Add Whitenoise for static files in production
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
import dj_database_url

DATABASE_URL = os.getenv("SUPABASE_DATABASE_URL") or os.getenv("SUPABASE_STRING") or os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }
    # Ensure sslmode=require for Supabase
    if 'OPTIONS' not in DATABASES['default']:
        DATABASES['default']['OPTIONS'] = {}
    DATABASES['default']['OPTIONS']['sslmode'] = os.getenv("POSTGRES_SSLMODE", "require")
else:
    # Fallback to individual vars if DATABASE_URL is missing
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

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
        print("❌ No PostgreSQL configuration found. Supabase connection required.")
        if DEBUG:
            print("⚠️ Falling back to SQLite for local development DEBUG mode only.")
            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': BASE_DIR / 'db.sqlite3',
                }
            }
        else:
            raise Exception("PostgreSQL environment variables are missing. Database connection is required for production.")

default_db = DATABASES.get('default', {})
print(f"🔌 DB backend: {default_db.get('ENGINE', '')}")
if default_db.get('ENGINE') == 'django.db.backends.postgresql':
    print(f"🔌 DB host: {default_db.get('HOST', '')}")
else:
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

# Enable WhiteNoise's Gzip compression of static assets.
# See: https://whitenoise.readthedocs.io/en/stable/django.html#infinitely-cacheable-assets-and-compression
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -----------------------------
# Cloudinary
# -----------------------------
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv("CLOUDINARY_CLOUD_NAME"),
    'API_KEY': os.getenv("CLOUDINARY_API_KEY"),
    'API_SECRET': os.getenv("CLOUDINARY_API_SECRET"),
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
