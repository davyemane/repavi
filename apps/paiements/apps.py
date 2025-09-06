from django.apps import AppConfig


class PaiementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.paiements'
    
    def ready(self):
        import apps.facturation.signals  # ✅ Pour écouter EcheancierPaiement