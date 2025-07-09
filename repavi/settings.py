"""
Configuration Django pour RepAvi Lodges
Production-ready avec sécurité renforcée
"""
import os
from pathlib import Path
from decouple import config, Csv

# === CONFIGURATION DE BASE ===
BASE_DIR = Path(__file__).resolve().parent.parent

# Clé secrète Django
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-change-me-in-production')

# Mode debug et détection d'environnement
DEBUG = config('DJANGO_DEBUG', default=True, cast=bool)  # Changé en True pour le développement
IS_PRODUCTION = not DEBUG

# Hôtes autorisés
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default=['localhost', '127.0.0.1', '*'])

# === MODÈLE UTILISATEUR PERSONNALISÉ ===
AUTH_USER_MODEL = 'users.User'

# === URLS D'AUTHENTIFICATION ===
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/users/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# === APPLICATIONS DJANGO ===
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'tailwind',
    'theme',
]

# Apps de développement
if DEBUG:
    THIRD_PARTY_APPS.extend([
        'django_browser_reload',
        # 'debug_toolbar',  # TEMPORAIREMENT DÉSACTIVÉ
    ])

# Applications du projet
LOCAL_APPS = [
    'users',        # Gestion utilisateurs
    'home',         # Page d'accueil et modèles de base
    'meubles',      # Gestion des meubles
    'reservations', # Gestion des réservations
    'avis'
]

# Liste finale des applications
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

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

# Middleware de développement
if DEBUG:
    MIDDLEWARE.append('django_browser_reload.middleware.BrowserReloadMiddleware')
    # MIDDLEWARE.insert(1, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # DÉSACTIVÉ

# Middleware de production
if IS_PRODUCTION:
    MIDDLEWARE.insert(1, 'django.middleware.gzip.GZipMiddleware')

# === CONFIGURATION DES URLS ===
ROOT_URLCONF = 'repavi.urls'
WSGI_APPLICATION = 'repavi.wsgi.application'

# === TEMPLATES ===
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
        },
    },
]

# === BASE DE DONNÉES ===
    # PostgreSQL en production
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME', default='repavi_db'),
        'USER': config('DB_USER', default='repavi_user'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'sslmode': 'prefer',
        },
        'CONN_MAX_AGE': 600,
    }
}

# === CACHE ===
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'repavi-cache',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

# === VALIDATION DES MOTS DE PASSE ===
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# === INTERNATIONALISATION ===
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = config('TIME_ZONE', default='Africa/Douala')
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
]

# === FICHIERS STATIQUES ===
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'theme' / 'static',
]

# Optimisation pour la production
if IS_PRODUCTION:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# === FICHIERS MULTIMÉDIA - CONFIGURATION CORRIGÉE ===
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Créer les dossiers média s'ils n'existent pas
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(MEDIA_ROOT / 'meubles' / 'photos', exist_ok=True)

# === CONFIGURATION TAILWIND ===
TAILWIND_APP_NAME = 'theme'

if IS_PRODUCTION:
    NPM_BIN_PATH = '/usr/bin/npm'
    TAILWIND_CSS_DEV_MODE = False
else:
    INTERNAL_IPS = ['127.0.0.1', '::1']
    NPM_BIN_PATH = config('NPM_BIN_PATH', default='npm')

# === SÉCURITÉ ===
# Protection CSRF
CSRF_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv(), default=[])

# Protection des sessions
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 1209600  # 2 semaines
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True

# Headers de sécurité
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# Configuration HTTPS pour la production
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SECURE_HSTS_SECONDS = 31536000  # 1 an
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# === CONFIGURATION DES UPLOADS - IMPORTANTE POUR LES PHOTOS ===
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB pour les photos
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Types de fichiers autorisés pour les uploads
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB maximum par image

# === CONFIGURATION EMAIL ===
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='RepAvi Lodges <noreply@repavilodges.com>')

# Configuration pour la production
if IS_PRODUCTION:
    ADMINS = [('Admin', config('ADMIN_EMAIL', default='admin@repavilodges.com'))]
    MANAGERS = ADMINS

# === URL DU SITE ===
SITE_URL = config('SITE_URL', default='http://127.0.0.1:8000' if DEBUG else 'https://repavilodges.com')

# === LOGGING ===
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'repavi.log',
            'maxBytes': 15 * 1024 * 1024,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'repavi': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# === MESSAGES FRAMEWORK ===
from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}

# === ADMINISTRATION ===
ADMIN_SITE_HEADER = 'RepAvi Lodges - Administration'
ADMIN_SITE_TITLE = 'RepAvi Admin'
ADMIN_INDEX_TITLE = 'Tableau de bord administrateur'

# === PARAMÈTRES MÉTIER REPAVI LODGES ===
REPAVI_SETTINGS = {
    'COMPANY_NAME': 'RepAvi Lodges',
    'COMPANY_ADDRESS': config('COMPANY_ADDRESS', default='Douala, Cameroun'),
    'COMPANY_PHONE': config('COMPANY_PHONE', default='+237 XXX XXX XXX'),
    'COMPANY_EMAIL': config('COMPANY_EMAIL', default='contact@repavilodges.com'),
    
    # WhatsApp pour réservations
    'WHATSAPP_NUMBER': config('WHATSAPP_NUMBER', default='+237XXXXXXXXX'),
    'WHATSAPP_MESSAGE_TEMPLATE': "Bonjour RepAvi Lodges, je souhaite faire une réservation pour l'appartement {appartement_numero}",
    
    # Paramètres des réservations
    'RESERVATION_AUTO_CONFIRM': config('RESERVATION_AUTO_CONFIRM', default=False, cast=bool),
    'RESERVATION_DEPOSIT_PERCENTAGE': config('RESERVATION_DEPOSIT_PERCENTAGE', default=30, cast=int),
    
    # Notifications
    'NOTIFICATION_BEFORE_CHECKIN': 24,
    'NOTIFICATION_BEFORE_CHECKOUT': 2,
    'NOTIFICATION_OVERDUE_PAYMENT': 48,
}

# === EXTENSIONS AUTORISÉES ===
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx']

# === DIVERS ===
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# === DÉVELOPPEMENT UNIQUEMENT ===
# DEBUG TOOLBAR DÉSACTIVÉ TEMPORAIREMENT
# if DEBUG:
#     try:
#         import debug_toolbar
#         INSTALLED_APPS.append('debug_toolbar')
#         MIDDLEWARE.insert(1, 'debug_toolbar.middleware.DebugToolbarMiddleware')
#         DEBUG_TOOLBAR_CONFIG = {
#             'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
#         }
#     except ImportError:
#         pass

# === INTÉGRATIONS FUTURES ===
# Google Maps
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')

# Twilio WhatsApp
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_WHATSAPP_NUMBER = config('TWILIO_WHATSAPP_NUMBER', default='')

# Réseaux sociaux
SOCIAL_MEDIA = {
    'FACEBOOK_URL': config('FACEBOOK_URL', default=''),
    'INSTAGRAM_URL': config('INSTAGRAM_URL', default=''),
    'TWITTER_URL': config('TWITTER_URL', default=''),
    'YOUTUBE_URL': config('YOUTUBE_URL', default=''),
}