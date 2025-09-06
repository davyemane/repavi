# ==========================================
# apps/facturation/apps.py - Configuration de l'app facturation
# ==========================================
from django.apps import AppConfig


class FacturationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.facturation'
    verbose_name = 'Facturation'
    
    def ready(self):
        """Importer les signaux quand l'app est prête"""
        import apps.facturation.signals
        
        # Optionnel: Créer les paramètres par défaut
        try:
            from .models import ParametresFacturation
            # S'assurer qu'il y a des paramètres par défaut
            ParametresFacturation.get_parametres()
        except Exception:
            # Ignorer les erreurs au démarrage (migration en cours, etc.)
            pass