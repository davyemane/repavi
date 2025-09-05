# ==========================================
# apps/facturation/apps.py
# ==========================================
from django.apps import AppConfig


class FacturationConfig(AppConfig):
    """
    Configuration de l'application facturation RepAvi Lodges
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.facturation'
    verbose_name = 'Facturation RepAvi'
    
    def ready(self):
        """
        Code exécuté quand l'application est prête
        """
        # Importer les signaux pour les enregistrer
        try:
            from . import signals
            signals.setup_signals()
        except ImportError:
            pass