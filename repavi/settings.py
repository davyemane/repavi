"""
Configuration Django pour RepAvi Lodges
Conforme au cahier des charges - Version simplifiée et sécurisée
"""
import os
from pathlib import Path
from decouple import config, Csv
import sys

# === CONFIGURATION DE BASE ===
BASE_DIR = Path(__file__).resolve().parent.parent

# Clé secrète Django
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-change-me-in-production')

# Mode debug et détection d'environnement
DEBUG = config('DJANGO_DEBUG', default=True, cast=bool)
IS_PRODUCTION = not DEBUG

# Hôtes autorisés
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default=['localhost', '127.0.0.1', '*'])

# === MODÈLE UTILISATEUR PERSONNALISÉ ===
AUTH_USER_MODEL = 'users.User'

# === URLS D'AUTHENTIFICATION ===
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# === APPLICATIONS DJANGO - CONFORMES AU CAHIER ===
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
     'apps.users',  
]

THIRD_PARTY_APPS = [
    'tailwind',
    'theme',
    'axes'
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',  # Ajoute ceci en premier
    'django.contrib.auth.backends.ModelBackend',  # ou ton backend d’authentification principal
]


# Apps de développement
if DEBUG:
    THIRD_PARTY_APPS.extend([
        'django_browser_reload',
    ])

# Applications RepAvi selon cahier des charges UNIQUEMENT
LOCAL_APPS = [
    
           # Profils : Super Admin + Gestionnaire
    'apps.appartements.apps.AppartementsConfig',   # Gestion appartements selon cahier
    'apps.clients.apps.ClientsConfig',        # Fiche client simple selon cahier
    'apps.reservations.apps.ReservationsConfig',   # Réservations et planning selon cahier
    'apps.paiements.apps.PaiementsConfig',      # Paiements par tranches SIMPLIFIÉ selon cahier
    'apps.inventaire.apps.InventaireConfig',     # Inventaire équipements SIMPLIFIÉ selon cahier
    'apps.comptabilite.apps.ComptabiliteConfig',   # Comptabilité simple selon cahier
    'apps.menage.apps.MenageConfig',         # Planning ménage basique selon cahier
    'apps.facturation.apps.FacturationConfig',    # Facturation PDF selon cahier 
    'apps.notifications.apps.NotificationsConfig',  # Notifications simples
]

# Liste finale des applications
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# === MIDDLEWARE ===
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.users.middleware.CurrentUserMiddleware', 
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
   
]

AXES_FAILURE_LIMIT = 3
AXES_COOLOFF_TIME = 300  # secondes (5 minutes)
AXES_LOCK_OUT_AT_FAILURE = True
AXES_RESET_ON_SUCCESS = True


# Middleware de développement
if DEBUG:
    MIDDLEWARE.append('django_browser_reload.middleware.BrowserReloadMiddleware')

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
        'APP_DIRS': False,  # On garde True, pas de loaders => pas de problème
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

# === BASE DE DONNÉES - PostgreSQL pour la fiabilité selon cahier ===
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME', default='repavi_lodges'),
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

# SQLite pour développement local si PostgreSQL indisponible
if DEBUG and not config('DB_PASSWORD', default=''):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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

# === VALIDATION DES MOTS DE PASSE SÉCURISÉS selon cahier ===
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
]

# === FICHIERS STATIQUES ===
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'theme' / 'static',
]

# Optimisation pour la production
if IS_PRODUCTION:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# === FICHIERS MULTIMÉDIA - PHOTOS selon cahier ===
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Créer les dossiers média selon la structure du cahier
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(MEDIA_ROOT / 'appartements' / 'photos', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'clients' / 'documents', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'inventaire', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'menage' / 'avant', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'menage' / 'apres', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'factures', exist_ok=True)

# === CONFIGURATION TAILWIND ===
TAILWIND_APP_NAME = 'theme'

if IS_PRODUCTION:
    NPM_BIN_PATH = '/usr/bin/npm'
    TAILWIND_CSS_DEV_MODE = False
else:
    INTERNAL_IPS = ['127.0.0.1', '::1']
    NPM_BIN_PATH = config('NPM_BIN_PATH', default='npm')

# === SÉCURITÉ RENFORCÉE selon cahier ===
# Protection CSRF
CSRF_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv(), default=[])

# Protection des sessions - Déconnexion automatique après 2h selon cahier
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 7200  # 2 heures selon cahier des charges
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Fermeture navigateur = déconnexion
SESSION_SAVE_EVERY_REQUEST = True

# Headers de sécurité
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# Configuration HTTPS pour la production selon cahier
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SECURE_HSTS_SECONDS = 31536000  # 1 an
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# === CONFIGURATION DES UPLOADS - PHOTOS selon cahier ===
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB pour les photos
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Types de fichiers autorisés selon cahier
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
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
    ADMINS = [('Admin RepAvi', config('ADMIN_EMAIL', default='admin@repavilodges.com'))]
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
ADMIN_SITE_HEADER = 'RepAvi Lodges - Administration de Backup'
ADMIN_SITE_TITLE = 'RepAvi Admin'
ADMIN_INDEX_TITLE = 'Interface de backup technique'

# === PARAMÈTRES MÉTIER REPAVI LODGES selon cahier ===
REPAVI_SETTINGS = {
    # Informations entreprise selon cahier
    'COMPANY_NAME': 'RepAvi Lodges',
    'COMPANY_ADDRESS': config('COMPANY_ADDRESS', default='Douala, Cameroun'),
    'COMPANY_PHONE': config('COMPANY_PHONE', default='+237 XXX XXX XXX'),
    'COMPANY_EMAIL': config('COMPANY_EMAIL', default='contact@repavilodges.com'),
    
    # Paramètres des réservations selon cahier
    'RESERVATION_ACOMPTE_PERCENTAGE': 40,  # 40% d'acompte selon cahier
    'RESERVATION_SOLDE_PERCENTAGE': 60,    # 60% de solde selon cahier
    
    # Délais selon cahier
    'DELAI_ACOMPTE_JOURS': 7,  # Acompte 7 jours avant arrivée
    'SESSION_TIMEOUT_HOURS': 2,  # Déconnexion après 2h selon cahier
    
    # Performance selon cahier
    'PAGE_LOAD_TARGET_SECONDS': 3,  # Pages en moins de 3 secondes
    'FORMATION_TARGET_HOURS': 2,    # Formation 2h maximum
    'MAX_CLICKS_ACTION': 3,          # Actions courantes en max 3 clics
    
    # Modes de paiement selon cahier (hors système)
    'MODES_PAIEMENT': [
        ('especes', 'Espèces'),
        ('virement', 'Virement bancaire'),
        ('mobile_money_orange', 'Mobile Money Orange'),
        ('mobile_money_mtn', 'Mobile Money MTN'),
        ('cheque', 'Chèque'),
    ],
    
    # États équipements selon cahier
    'ETATS_EQUIPEMENTS': [
        ('bon', 'Bon'),
        ('usage', 'Usage'),
        ('defectueux', 'Défectueux'),
        ('hors_service', 'Hors service'),
    ],
}

# === PERFORMANCE selon cahier (pages en moins de 3 secondes) ===
# Cache pour les templates
if IS_PRODUCTION:
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]

# === SAUVEGARDES AUTOMATIQUES selon cahier ===
# Configuration pour sauvegardes quotidiennes automatiques
BACKUP_SETTINGS = {
    'BACKUP_DIR': BASE_DIR / 'backups',
    'BACKUP_TIME': '02:00',  # 2h du matin
    'BACKUP_RETENTION_DAYS': 30,  # Garder 30 jours
    'BACKUP_COMPRESS': True,
}

# Créer le dossier de sauvegarde
os.makedirs(BACKUP_SETTINGS['BACKUP_DIR'], exist_ok=True)

# === EXTENSIONS AUTORISÉES selon cahier ===
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf']

# === FACTURATION PDF selon cahier ===
FACTURE_SETTINGS = {
    'LOGO_PATH': STATIC_ROOT / 'images' / 'logo_repavi.png',
    'TEMPLATE_PDF': 'facturation/facture_template.html',
    'NUMEROTATION_PREFIX': 'FAC',
    'NUMEROTATION_YEAR': True,
}

# === LIMITS selon cahier (simplicité) ===
# Limites pour éviter la complexité
MAX_APPARTEMENTS_PAR_MAISON = 50
MAX_EQUIPEMENTS_PAR_APPARTEMENT = 20
MAX_PHOTOS_PAR_APPARTEMENT = 10
MAX_RESERVATIONS_PAR_MOIS = 200

# === VALIDATION selon cahier ===
# Critères d'acceptation du cahier des charges
VALIDATION_CRITERIA = {
    'CREATION_APPARTEMENT_MAX_MINUTES': 2,
    'CREATION_RESERVATION_MAX_MINUTES': 5,
    'DEFINITION_ECHEANCIER_MAX_MINUTES': 1,
    'CHANGEMENT_STATUT_MAX_CLICS': 1,
    'FORMATION_MAX_HEURES': 2,
}

# === DIVERS ===
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# === DÉVELOPPEMENT UNIQUEMENT ===
if DEBUG:
    # Données de test
    FIXTURE_DIRS = [BASE_DIR / 'fixtures']
    
    # Emails en console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# === PRODUCTION UNIQUEMENT ===
if IS_PRODUCTION:
    # Compression statiques
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
    
    # Optimisations base de données
    DATABASES['default']['OPTIONS'] = {
        'sslmode': 'require',
    }


# === FONCTIONNALITÉS EXCLUES du cahier ===
# Ces fonctionnalités sont EXPLICITEMENT exclues du cahier des charges
EXCLUDED_FEATURES = {
    'ONLINE_BOOKING_BY_CLIENTS': False,      # Réservations en ligne par clients
    'EXTERNAL_INTEGRATIONS': False,          # Booking.com, Airbnb
    'AUTOMATIC_ONLINE_PAYMENTS': False,      # Paiements en ligne automatiques
    'ADVANCED_ANALYTICS': False,             # Analytics avancées
    'MOBILE_APP': False,                     # Application mobile
    'COMPLEX_SECURITY_SYSTEM': False,        # Système de sécurité complexe
    'PUBLIC_HOMEPAGE': False,                # Page d'accueil publique
}

# === ÉQUIPEMENTS PRÉDÉFINIS selon cahier ===
# Liste simple d'équipements pour les appartements
EQUIPEMENTS_PREDEFINED = [
    'TV',
    'Frigo', 
    'Climatisation',
    'Micro-ondes',
    'Bouilloire',
    'Canapé',
    'Table basse',
    'Lit double',
    'Armoire',
    'Chaises',
    'Wifi',
    'Balcon',
    'Parking',
    'Sécurité 24h',
    'Générateur',
]

# === TYPES D'APPARTEMENTS selon cahier ===
TYPES_APPARTEMENTS = [
    ('studio', 'Studio'),
    ('t1', 'T1'),
    ('t2', 'T2'),
]

# === STATUTS selon cahier ===
STATUTS_APPARTEMENTS = [
    ('disponible', 'Disponible'),
    ('occupe', 'Occupé'),
    ('maintenance', 'Maintenance'),
]

STATUTS_RESERVATIONS = [
    ('confirmee', 'Confirmée'),
    ('en_cours', 'En cours'),
    ('terminee', 'Terminée'),
    ('annulee', 'Annulée'),
]

STATUTS_PAIEMENTS = [
    ('en_attente', 'En attente'),
    ('paye', 'Payé'),
]

STATUTS_MENAGE = [
    ('a_faire', 'À faire'),
    ('en_cours', 'En cours'),
    ('termine', 'Terminé'),
]

# === PERMISSIONS selon cahier ===
# Matrice des permissions définie dans le cahier des charges
PERMISSIONS_MATRIX = {
    'super_admin': {
        'gestion_appartements': True,
        'gestion_clients': True,
        'reservations': True,
        'paiements': True,
        'inventaire': True,
        'comptabilite': True,
        'menage': True,
        'facturation': True,
        'rapports': True,
        'gestion_gestionnaires': True,  # Seul le super admin
    },
    'gestionnaire': {
        'gestion_appartements': True,
        'gestion_clients': True,
        'reservations': True,
        'paiements': True,
        'inventaire': True,
        'comptabilite': True,
        'menage': True,
        'facturation': True,
        'rapports': True,
        'gestion_gestionnaires': False,  # Pas de gestion d'autres gestionnaires
    },
}

# === MÉTRIQUES DE PERFORMANCE selon cahier ===
# Objectifs de performance définis dans le cahier
PERFORMANCE_TARGETS = {
    'PAGE_LOAD_TIME_SECONDS': 3,
    'SEARCH_RESPONSE_TIME_MS': 500,
    'AUTO_SAVE_INTERVAL_SECONDS': 30,
    'SESSION_TIMEOUT_MINUTES': 120,  # 2 heures
}

# === FORMATS DE DONNÉES ===
# Formats d'affichage selon contexte camerounais
DATE_FORMAT = 'd/m/Y'
SHORT_DATE_FORMAT = 'd/m/y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'd/m/Y H:i'

# Format monétaire FCFA
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = ' '
NUMBER_GROUPING = 3

# === INTÉGRATIONS FUTURES (Hors scope actuel) ===
# Préparation pour évolutions futures si demandées
FUTURE_INTEGRATIONS = {
    'GOOGLE_MAPS_API_KEY': config('GOOGLE_MAPS_API_KEY', default=''),
    'WHATSAPP_API': {
        'ENABLED': False,  # Non requis par cahier actuel
        'NUMBER': config('WHATSAPP_NUMBER', default=''),
    },
    'SMS_NOTIFICATIONS': {
        'ENABLED': False,  # Non requis par cahier actuel
        'PROVIDER': config('SMS_PROVIDER', default=''),
    },
}

# === MAINTENANCE ET MONITORING ===
# Pour assurer les 99% de disponibilité mentionnés dans le cahier
MAINTENANCE_MODE = config('MAINTENANCE_MODE', default=False, cast=bool)
HEALTH_CHECK_ENABLED = True

# === DONNÉES DE TEST pour formation selon cahier ===
if DEBUG:
    LOAD_TEST_DATA = config('LOAD_TEST_DATA', default=True, cast=bool)
    TEST_DATA_SETTINGS = {
        'NB_APPARTEMENTS_TEST': 5,
        'NB_CLIENTS_TEST': 10,
        'NB_RESERVATIONS_TEST': 15,
        'GENERATE_PHOTOS': False,  # Éviter de générer des photos en test
    }