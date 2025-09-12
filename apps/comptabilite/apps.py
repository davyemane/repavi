from django.apps import AppConfig


class ComptabiliteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.comptabilite'

    def ready(self):
        """Importer les signaux"""
        try:
            import apps.comptabilite.signals
        except ImportError:
            pass