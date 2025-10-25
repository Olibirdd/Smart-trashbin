import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Secret key
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "fallback-secret-key")

# Debug mode (False for production)
DEBUG = False

# Allowed hosts (your Render app URL)
ALLOWED_HOSTS = [
    'smart-bin-web.onrender.com',
    'localhost',
    '127.0.0.1',
    '.onrender.com'  # This allows any subdomain of onrender.com
]

# Installed apps
INSTALLED_APPS = [
    # Default Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Your app
    'vending_machine',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # for serving static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Root URL configuration
ROOT_URLCONF = 'smart_vending_machine.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "vending_machine" / "templates"],
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

# WSGI application
WSGI_APPLICATION = 'smart_vending_machine.wsgi.application'

# Database (MongoDB using Djongo)
DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': 'smart_vending',
        'ENFORCE_SCHEMA': False,
        'CLIENT': {
            'host': os.environ.get("MONGO_URI"),
        }
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Localization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "vending_machine" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login redirects
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
