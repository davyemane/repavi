import os
from pathlib import Path

# === BASE DIR ===
BASE_DIR = Path(__file__).resolve().parent.parent

# === SECRET KEY ===
SECRET_KEY = 'django-insecure-082n3q0&(q!4p((fti#g^prqwqnueq)zxl82g!69ob88mm9ui5'

# === DEBUG & ENV DETECTION ===
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'  # mettre à '0' en production
IS_PRODUCTION = not DEBUG

# === ALLOWED HOSTS ===
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'repavilodges.com', 'www.repavilodges.com']

# === SECURITÉ CONDITIONNELLE ===
SECURE_SSL_REDIRECT = IS_PRODUCTION
SESSION_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_SECURE = IS_PRODUCTION
SECURE_BROWSER_XSS_FILTER = IS_PRODUCTION
SECURE_CONTENT_TYPE_NOSNIFF = IS_PRODUCTION
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # important avec Nginx ou autre proxy

TAILWIND_APP_NAME = 'theme'


# === APPLICATIONS ===
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Tailwind
    'tailwind',
    'theme',
    'django_browser_reload',  # Pour le reload automatique
    
    # Votre app
    'home',
]

# === MIDDLEWARE ===
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# === URLS & WSGI ===
ROOT_URLCONF = 'repavi.urls'
WSGI_APPLICATION = 'repavi.wsgi.application'

# === TEMPLATES ===
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # ← Ajoutez cette ligne
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
# === BASE DE DONNÉES ===
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'repavi',
        'USER': 'repaviuser',
        'PASSWORD': 'Felicien@2002',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# === VALIDATION DES MOTS DE PASSE ===
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# === LANGUE & TEMPS ===
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# === FICHIERS STATIQUES ===
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# === FICHIERS MULTIMÉDIA ===
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# === AUTO FIELD PAR DÉFAUT ===
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'