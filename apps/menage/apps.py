from django.apps import AppConfig


class MenageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.menage'
    verbose_name = 'Ménage'

    def ready(self):
        # Importer les signaux
        import apps.menage.signals