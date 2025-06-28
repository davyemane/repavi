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
CSRF_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv(), default=[])
CSRF_FAILURE_VIEW = 'utils.views.csrf_failure'

# Protection des sessions
SESSION_COOKIE_SECURE = IS_PRODUCTION
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
if IS_PRODUCTION:
    SECURE_HSTS_SECONDS = 31536000  # 1 an
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Protection des uploads
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
FILE_UPLOAD_PERMISSIONS = 0o644
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Extensions autorisées
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx']

# Protection contre le clickjacking
X_FRAME_OPTIONS = 'DENY'

# === APPLICATIONS ===
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # Pour formater les nombres, dates
    
    # Outils de développement
    'django_extensions',  # Commandes utiles comme shell_plus
    
    # Tailwind et UI
    'tailwind',
    'theme',
    'django_browser_reload',
    
    # Génération PDF selon cahier des charges
    'weasyprint',
    
    # Rate limiting pour sécurité
    'django_ratelimit',
    
    # Apps principales selon cahier des charges
    'users',       # Gestion utilisateurs (Client, Gestionnaire, Super Admin)
    'home',        # Vitrine publique + modèles principaux
    'reservations', # Gestion des réservations 
    'appartements', # Gestion des appartements
    'meubles',     # Gestion des meubles
    'avis',        # Système d'avis clients
    'statistics',  # Statistiques et rapports
    'notifications', # Système de notifications (WhatsApp futur)
]

# === MIDDLEWARE AVEC SÉCURITÉ ===
MIDDLEWARE = [
    # Sécurité en premier
    'django.middleware.security.SecurityMiddleware',
    
    # Monitoring des performances
    'utils.middleware.PerformanceMonitoringMiddleware',
    
    # Rate limiting pour protection
    'django_ratelimit.middleware.RatelimitMiddleware',
    
    # Middlewares Django standard
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Middleware personnalisé pour logging sécurisé
    'utils.middleware.SecurityLoggingMiddleware',
    
    # Reload en développement seulement
] + (['django_browser_reload.middleware.BrowserReloadMiddleware'] if DEBUG else [])

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
                # Context processor personnalisé pour variables globales
                'utils.context_processors.global_settings',
            ],
        },
    },
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

# === CACHE SELON ENVIRONNEMENT ===
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
    # Cache local pour développement
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'repavi-cache',
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
    # Validateur personnalisé pour plus de sécurité
    {
        'NAME': 'utils.validators.CustomPasswordValidator',
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
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / "static",
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

if IS_PRODUCTION:
    # Configuration SMTP pour production
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
    
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='RepAvi Lodges <noreply@repavilodges.com>')
ADMINS = [('Admin', config('ADMIN_EMAIL', default='admin@repavilodges.com'))]
MANAGERS = ADMINS

# === SITE URL ===
SITE_URL = config('SITE_URL_PROD' if IS_PRODUCTION else 'SITE_URL_DEV', 
                 default='https://repavilodges.com' if IS_PRODUCTION else 'http://127.0.0.1:8000')

# === TAILWIND ===
TAILWIND_APP_NAME = 'theme'
NPM_BIN_PATH = config('NPM_BIN_PATH', default='npm')

# === LOGGING SÉCURISÉ ===
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
        'security': {
            'format': 'SECURITY {asctime} {levelname} {module} {funcName} {message} - IP: {extra[ip]} - User: {extra[user]}',
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
        'security': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'security.log',
            'maxBytes': 1024*1024*5,  # 5MB
            'backupCount': 5,
            'formatter': 'security',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
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
        'repavi.security': {
            'handlers': ['security', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# === GÉNÉRATION DE PDF (selon cahier des charges) ===
# Configuration WeasyPrint
WEASYPRINT_BASEURL = SITE_URL
WEASYPRINT_CSS = [
    BASE_DIR / 'static' / 'css' / 'pdf_styles.css'
]

# === NOTIFICATIONS WHATSAPP (futur) ===
# Configuration pour intégration future Twilio WhatsApp
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_WHATSAPP_NUMBER = config('TWILIO_WHATSAPP_NUMBER', default='')

# === RATE LIMITING ===
RATELIMIT_ENABLE = True
RATELIMIT_VIEW = 'utils.views.ratelimited'

# Limites par défaut
DEFAULT_RATE_LIMITS = {
    'login': '5/5m',        # 5 tentatives par 5 minutes
    'register': '3/h',       # 3 inscriptions par heure par IP
    'contact': '10/h',       # 10 messages de contact par heure
    'reservation': '20/h',   # 20 réservations par heure
    'pdf_generation': '50/h', # 50 PDFs par heure
}

# === PARAMÈTRES MÉTIER SELON CAHIER DES CHARGES ===
# Configuration spécifique à RepAvi Lodges
REPAVI_SETTINGS = {
    'COMPANY_NAME': 'RepAvi Lodges',
    'COMPANY_ADDRESS': config('COMPANY_ADDRESS', default='Douala, Cameroun'),
    'COMPANY_PHONE': config('COMPANY_PHONE', default='+237 XXX XXX XXX'),
    'COMPANY_EMAIL': config('COMPANY_EMAIL', default='contact@repavilodges.com'),
    
    # WhatsApp pour réservations directes
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

# === VARIABLES D'ENVIRONNEMENT SPÉCIFIQUES ===
# Google Maps pour localisation des appartements
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')

# Réseaux sociaux (pour vitrine)
SOCIAL_MEDIA = {
    'FACEBOOK_URL': config('FACEBOOK_URL', default=''),
    'INSTAGRAM_URL': config('INSTAGRAM_URL', default=''),
    'TWITTER_URL': config('TWITTER_URL', default=''),
    'YOUTUBE_URL': config('YOUTUBE_URL', default=''),
}

# === PERFORMANCE & OPTIMISATION ===
# Cache des templates en production
if IS_PRODUCTION:
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]

# Compression des réponses en production
if IS_PRODUCTION:
    MIDDLEWARE.insert(1, 'django.middleware.gzip.GZipMiddleware')

# === BACKUP ET MAINTENANCE ===
# Configuration pour sauvegardes automatiques
BACKUP_SETTINGS = {
    'DB_BACKUP_DIR': BASE_DIR / 'backups' / 'db',
    'MEDIA_BACKUP_DIR': BASE_DIR / 'backups' / 'media',
    'RETENTION_DAYS': 30,
    'BACKUP_SCHEDULE': 'daily',  # daily, weekly, monthly
}

# === MONITORING ===
# Seuils d'alerte
MONITORING_THRESHOLDS = {
    'SLOW_REQUEST_THRESHOLD': 2.0,  # secondes
    'HIGH_MEMORY_THRESHOLD': 80,    # pourcentage
    'ERROR_RATE_THRESHOLD': 5,      # pourcentage
}

# === AUTO FIELD PAR DÉFAUT ===
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# === SÉCURITÉ ADDITIONNELLE EN PRODUCTION ===
if IS_PRODUCTION:
    # Protection supplémentaire
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    
    # Désactiver le debug en production
    DEBUG = False
    TEMPLATE_DEBUG = False
    
    # Logs d'erreurs par email
    LOGGING['handlers']['mail_admins']['level'] = 'ERROR'
    
    # Masquer les informations sensibles dans les logs
    import django.utils.log
    django.utils.log.DEFAULT_LOGGING['loggers']['django.security.DisallowedHost'] = {
        'handlers': ['null'],
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

# === ADMIN CUSTOMIZATION ===
ADMIN_SITE_HEADER = 'RepAvi Lodges - Administration'
ADMIN_SITE_TITLE = 'RepAvi Admin'
ADMIN_INDEX_TITLE = 'Tableau de bord administrateur'

# === DÉVELOPPEMENT SEULEMENT ===
if DEBUG:
    # Debug toolbar
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
    
    # Emails en console en développement
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'