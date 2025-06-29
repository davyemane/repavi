from django.apps import AppConfig


class MeublesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'meubles'
    verbose_name = 'Gestion des Meubles'
    
    def ready(self):
        # Import des signaux si nécessaire
        try:
            import meubles.signals
        except ImportError:
            pass