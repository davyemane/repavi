# avis/apps.py
from django.apps import AppConfig

class AvisConfig(AppConfig):
    """Configuration de l'application Avis"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'avis'
    verbose_name = 'Système d\'avis et notations'
    
    def ready(self):
        """Actions à effectuer quand l'app est prête"""
        # Import des signals si nécessaire
        try:
            import avis.signals
        except ImportError:
            pass