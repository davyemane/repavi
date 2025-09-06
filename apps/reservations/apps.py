from django.apps import AppConfig


class ReservationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reservations'

    def ready(self):
        import apps.facturation.signals  # ✅ Pour écouter EcheancierPaiement
