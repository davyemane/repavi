# apps/users/apps.py
from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'Utilisateurs'
    
    def ready(self):
        # Importer les signaux pour qu'ils soient enregistrés
        try:
            import apps.users.signals
        except ImportError:
            pass