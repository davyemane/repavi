import os
from pathlib import Path
from decouple import config, Csv

# === BASE DIR ===
BASE_DIR = Path(__file__).resolve().parent.parent

# === SECRET KEY ===
SECRET_KEY = config('DJANGO_SECRET_KEY')

# === DEBUG & ENV DETECTION ===
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)
IS_PRODUCTION = not DEBUG

# === ALLOWED HOSTS ===
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# === MODÈLE UTILISATEUR PERSONNALISÉ ===
AUTH_USER_MODEL = 'users.User'

# === AUTHENTIFICATION ===
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/users/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# === SÉCURITÉ RENFORCÉE ===
# Protection CSRF
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=IS_PRODUCTION, cast=bool)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv(), default=[])

# Protection des sessions
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=IS_PRODUCTION, cast=bool)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE', default=1209600, cast=int)  # 2 semaines
SESSION_EXPIRE_AT_BROWSER_CLOSE = config('SESSION_EXPIRE_AT_BROWSER_CLOSE', default=False, cast=bool)
SESSION_SAVE_EVERY_REQUEST = config('SESSION_SAVE_EVERY_REQUEST', default=True, cast=bool)

# Headers de sécurité
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=IS_PRODUCTION, cast=bool)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Sécurité HTTPS en production
if IS_PRODUCTION:
    SECURE_HSTS_SECONDS = 31536000  # 1 an
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Protection des uploads
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
FILE_UPLOAD_PERMISSIONS = 0o644
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Protection contre le clickjacking
X_FRAME_OPTIONS = 'DENY'

# === TAILWIND ===
TAILWIND_APP_NAME = 'theme'
# Configuration spécifique pour la production
if IS_PRODUCTION:
    # Chemin vers Node.js en production
    NPM_BIN_PATH = '/usr/bin/npm'  # ou le chemin correct sur votre VPS
    
    # Configuration pour la compilation en production
    TAILWIND_CSS_DEV_MODE = False
    
    # Assurez-vous que les fichiers CSS sont bien générés
    STATICFILES_DIRS = [
        BASE_DIR / "theme/static",
        BASE_DIR / "theme/static_src/dist",  # Ajoutez ce chemin
    ]
else:
    INTERNAL_IPS = ['127.0.0.1', '::1']
    NPM_BIN_PATH = config('NPM_BIN_PATH', default='npm')

# Modifiez cette partie dans votre STATICFILES_DIRS
STATICFILES_DIRS = [
    BASE_DIR / "theme/static",
    BASE_DIR / "theme/static_src/dist",  # Ajoutez cette ligne
]
# === APPLICATIONS ===
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # Pour formater les nombres, dates
    
    # Tailwind et UI
    'tailwind',
    'theme',
    'django_browser_reload',
    
    # Apps du projet selon cahier des charges
    'users',       # Gestion utilisateurs (Client, Gestionnaire, Super Admin)
    'home',        # Vitrine publique + modèles principaux
    # 'meubles',      # Gestion des meubles
    'meubles',      # Gestion des meubles
    'reservations.apps.ReservationsConfig',   # Gestion des réservations

]

# Apps optionnelles selon le développement
OPTIONAL_APPS = [
    # 'reservations',   # Gestion des réservations 
    # 'appartements',   # Gestion des appartements
    # 'meubles',        # Gestion des meubles
    # 'avis',           # Système d'avis clients
    # 'statistics',     # Statistiques et rapports
    # 'notifications',  # Système de notifications (WhatsApp futur)
]

# Ajouter les apps optionnelles qui existent
for app in OPTIONAL_APPS:
    app_path = BASE_DIR / app
    if app_path.exists() and (app_path / '__init__.py').exists():
        INSTALLED_APPS.append(app)

# === MIDDLEWARE ===
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware'
]

# Middleware conditionnel
if DEBUG:
    MIDDLEWARE.append('django_browser_reload.middleware.BrowserReloadMiddleware')

if IS_PRODUCTION:
    # Compression en production
    MIDDLEWARE.insert(1, 'django.middleware.gzip.GZipMiddleware')

# === URLS & WSGI ===
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
            ],
        },
    },
]

# Cache des templates en production
if IS_PRODUCTION:
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]

# === BASE DE DONNÉES ===
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'sslmode': 'require' if IS_PRODUCTION else 'prefer',
        },
        # Pool de connexions pour production
        'CONN_MAX_AGE': 600 if IS_PRODUCTION else 0,
    }
}

# === CACHE ===
if IS_PRODUCTION:
    # Redis pour production
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
else:
    # Cache simple pour développement
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
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
TIME_ZONE = config('TIME_ZONE', default='Africa/Douala')  # Cameroun selon projet
USE_I18N = True
USE_TZ = True

# Langues supportées pour l'avenir
LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
]

# === FICHIERS STATIQUES ===
STATIC_URL = 'theme/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / "theme/static"
]

# Optimisation des fichiers statiques en production
if IS_PRODUCTION:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# === FICHIERS MULTIMÉDIA ===
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Structure des dossiers media selon cahier des charges
MEDIA_SUBDIRS = {
    'APPARTEMENTS_PHOTOS': 'appartements/photos/',
    'MEUBLES_PHOTOS': 'meubles/photos/',
    'CLIENTS_DOCUMENTS': 'clients/documents/',
    'USERS_PHOTOS': 'users/photos/',
    'PDFS_GENERATED': 'pdfs/',
}

# === EMAIL CONFIGURATION ===
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='RepAvi Lodges <noreply@repavilodges.com>')

# Configuration email pour production
if IS_PRODUCTION:
    ADMINS = [('Admin', config('ADMIN_EMAIL', default='admin@repavilodges.com'))]
    MANAGERS = ADMINS

# === SITE URL ===
if DEBUG:
    SITE_URL = config('SITE_URL_DEV', default='http://127.0.0.1:8000')
else:
    SITE_URL = config('SITE_URL_PROD', default='https://repavilodges.com')

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
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'repavi.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] + (['mail_admins'] if IS_PRODUCTION else []),
            'level': 'INFO',
        },
        'repavi': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# === PARAMÈTRES MÉTIER REPAVI LODGES ===
# Configuration spécifique selon cahier des charges
REPAVI_SETTINGS = {
    'COMPANY_NAME': 'RepAvi Lodges',
    'COMPANY_ADDRESS': config('COMPANY_ADDRESS', default='Douala, Cameroun'),
    'COMPANY_PHONE': config('COMPANY_PHONE', default='+237 XXX XXX XXX'),
    'COMPANY_EMAIL': config('COMPANY_EMAIL', default='contact@repavilodges.com'),
    
    # WhatsApp pour réservations directes selon cahier des charges
    'WHATSAPP_NUMBER': config('WHATSAPP_NUMBER', default='+237XXXXXXXXX'),
    'WHATSAPP_MESSAGE_TEMPLATE': "Bonjour RepAvi Lodges, je souhaite faire une réservation pour l'appartement {appartement_numero}",
    
    # Paramètres des avis
    'AVIS_REQUIRE_MODERATION': config('AVIS_REQUIRE_MODERATION', default=False, cast=bool),
    'AVIS_MAX_PER_RESERVATION': 1,
    
    # Paramètres des réservations
    'RESERVATION_AUTO_CONFIRM': config('RESERVATION_AUTO_CONFIRM', default=False, cast=bool),
    'RESERVATION_DEPOSIT_PERCENTAGE': config('RESERVATION_DEPOSIT_PERCENTAGE', default=30, cast=int),
    
    # Délais de notification (en heures)
    'NOTIFICATION_BEFORE_CHECKIN': 24,
    'NOTIFICATION_BEFORE_CHECKOUT': 2,
    'NOTIFICATION_OVERDUE_PAYMENT': 48,
}

# === INTÉGRATIONS FUTURES ===
# Google Maps pour localisation des appartements
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')

# Notifications WhatsApp (futur avec Twilio)
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_WHATSAPP_NUMBER = config('TWILIO_WHATSAPP_NUMBER', default='')

# Réseaux sociaux pour vitrine
SOCIAL_MEDIA = {
    'FACEBOOK_URL': config('FACEBOOK_URL', default=''),
    'INSTAGRAM_URL': config('INSTAGRAM_URL', default=''),
    'TWITTER_URL': config('TWITTER_URL', default=''),
    'YOUTUBE_URL': config('YOUTUBE_URL', default=''),
}

# === EXTENSIONS AUTORISÉES ===
# Pour validation des uploads selon sécurité
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx']

# === AUTO FIELD PAR DÉFAUT ===
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# === MESSAGES FRAMEWORK ===
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}

# === ADMINISTRATION PERSONNALISÉE ===
ADMIN_SITE_HEADER = 'RepAvi Lodges - Administration'
ADMIN_SITE_TITLE = 'RepAvi Admin'
ADMIN_INDEX_TITLE = 'Tableau de bord administrateur'

# === DÉVELOPPEMENT SEULEMENT ===
if DEBUG:
    # Debug toolbar (optionnel)
    try:
        import debug_toolbar
        INSTALLED_APPS.append('debug_toolbar')
        MIDDLEWARE.insert(1, 'debug_toolbar.middleware.DebugToolbarMiddleware')
        INTERNAL_IPS = ['127.0.0.1', '::1']
        DEBUG_TOOLBAR_CONFIG = {
            'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
        }
    except ImportError:
        pass
    
    # Emails en console pour développement
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# === FONCTIONNALITÉS AVANCÉES (À ACTIVER PROGRESSIVEMENT) ===
# Décommentez au fur et à mesure du développement

# # Génération PDF (WeasyPrint)
# try:
#     import weasyprint
#     INSTALLED_APPS.append('weasyprint')
#     WEASYPRINT_BASEURL = SITE_URL
#     WEASYPRINT_CSS = [BASE_DIR / 'static' / 'css' / 'pdf_styles.css']
# except ImportError:
#     pass

# # Rate limiting (pour production)
# if IS_PRODUCTION:
#     try:
#         import django_ratelimit
#         INSTALLED_APPS.append('django_ratelimit')
#         MIDDLEWARE.insert(2, 'django_ratelimit.middleware.RatelimitMiddleware')
#         RATELIMIT_ENABLE = True
#         RATELIMIT_VIEW = 'utils.views.ratelimited'
#     except ImportError:
#         pass

# # Django extensions (utilitaires de développement)
# if DEBUG:
#     try:
#         import django_extensions
#         INSTALLED_APPS.append('django_extensions')
#     except ImportError:
#         pass
