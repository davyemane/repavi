# reservations/apps.py - Configuration de l'application réservations

from django.apps import AppConfig


class ReservationsConfig(AppConfig):
    """Configuration de l'application réservations"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reservations'
    verbose_name = 'Réservations'
    
    def ready(self):
        """Actions à effectuer quand l'application est prête"""
        # Importer les signaux
        import reservations.signals