from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.reservations.models import Reservation
from .models import TacheMenage


@receiver(post_save, sender=Reservation)
def creer_tache_menage_apres_depart(sender, instance, created, **kwargs):
    """
    Crée automatiquement une tâche de ménage le jour du départ
    quand une réservation se termine
    """
    # Vérifier si la réservation vient de passer en statut 'termine'
    if instance.statut == 'termine':
        # Créer tâche uniquement si elle n'existe pas déjà
        TacheMenage.objects.get_or_create(
            appartement=instance.appartement,
            date_prevue=instance.date_depart,
            defaults={
                'reservation': instance,
                'statut': 'a_faire'
            }
        )