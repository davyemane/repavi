from datetime import timezone
from django.urls import reverse
from apps.notifications.models import Notification
from apps.users.models import User


class NotificationService:
    """Service pour créer des notifications contextuelles"""
    
    @staticmethod
    def notify_reservation_created(reservation, actor):
        # Notifier les gestionnaires
        from apps.users.models import User
        gestionnaires = User.objects.filter(profil__in=['gestionnaire', 'super_admin'])
        
        for user in gestionnaires:
            if user != actor:
                Notification.objects.create(
                    user=user,
                    type='reservation',
                    action='created',
                    title='Nouvelle réservation',
                    message=f'{actor.first_name or actor.username} a créé une réservation pour {reservation.client.nom}',
                    actor=actor,
                    url=reverse('reservations:detail', kwargs={'pk': reservation.pk}),
                    url_text='Voir la réservation',
                    object_type='reservation',
                    object_id=reservation.pk,
                    object_name=f'Réservation #{reservation.pk}'
                )
    
    @staticmethod
    def notify_menage_assigned(tache, assigned_user, actor):
        Notification.objects.create(
            user=assigned_user,
            type='menage',
            action='assigned',
            title='Tâche ménage assignée',
            message=f'Vous avez été affecté au ménage de l\'appartement {tache.appartement.numero}',
            actor=actor,
            url=reverse('menage:checklist', kwargs={'pk': tache.pk}),
            url_text='Voir la tâche',
            object_type='menage',
            object_id=tache.pk,
            object_name=f'Ménage {tache.appartement.numero}'
        )
    
    @staticmethod
    def notify_paiement_overdue(echeance):
        # Notifier tous les gestionnaires
        from apps.users.models import User
        gestionnaires = User.objects.filter(profil__in=['gestionnaire', 'super_admin'])
        
        for user in gestionnaires:
            Notification.objects.create(
                user=user,
                type='paiement',
                action='overdue',
                title='Paiement en retard',
                message=f'Le paiement de {echeance.reservation.client.nom} est en retard depuis {(timezone.now().date() - echeance.date_echeance).days} jours',
                url=reverse('paiements:saisir', kwargs={'pk': echeance.pk}),
                url_text='Saisir paiement',
                object_type='paiement',
                object_id=echeance.pk,
                object_name=f'{echeance.get_type_paiement_display()} - {echeance.montant_prevu} FCFA'
            )

    @staticmethod
    def notify_paiement_received(echeance, actor):
        gestionnaires = User.objects.filter(profil__in=['gestionnaire', 'super_admin'])
        for user in gestionnaires:
            if user != actor:
                Notification.objects.create(
                    user=user,
                    type='paiement',
                    action='completed',
                    title='Paiement reçu',
                    message=f'{actor.first_name} a enregistré un paiement de {echeance.montant_paye} FCFA',
                    actor=actor,
                    url=reverse('paiements:echeancier'),
                    object_type='paiement',
                    object_id=echeance.pk
                )

    @staticmethod
    def paiements_overdue():
        # Notifier tous les gestionnaires
        gestionnaires = User.objects.filter(profil__in=['gestionnaire', 'super_admin'])
        
        for user in gestionnaires:
            Notification.objects.create(
                user=user,
                type='paiement',
                action='overdue',
                title='Paiement en retard',
                message='Vous avez des paiements en retard',
                url=reverse('paiements:echeancier'),
                url_text='Voir les paiements',
                object_type='paiement',
                object_id=None
            )

    @staticmethod    
    def notify_appartement_created(appartement, actor):
        Notification.objects.create(
            user=actor,
            type='appartement',
            action='created',
            title='Nouvel appartement',
            message=f'{actor.first_name} a créé un nouvel appartement',
            actor=actor,
            url=reverse('appartements:detail', kwargs={'pk': appartement.pk}),
            url_text='Voir l\'appartement',
            object_type='appartement',
            object_id=appartement.pk
        )

    @staticmethod    
    def notify_appartement_updated(appartement, actor):
        Notification.objects.create(
            user=actor,
            type='appartement',
            action='updated',
            title='Appartement modifié',
            message=f'{actor.first_name} a modifié l\'appartement',
            actor=actor,
            url=reverse('appartements:detail', kwargs={'pk': appartement.pk}),
            url_text='Voir l\'appartement',
            object_type='appartement',
            object_id=appartement.pk
        )   

    @staticmethod    
    def notify_photo_deleted(photo, actor):
        Notification.objects.create(
            user=actor,
            type='appartement',
            action='deleted',
            title='Photo supprimée',
            message=f'{actor.first_name} a supprimé la photo',
            actor=actor,
            url=reverse('appartements:photos'),
            url_text='Voir les photos',
            object_type='appartement',
            object_id=photo.appartement.pk
        )

    @staticmethod
    def notify_appartement_maintenance(appartement, actor):
        gestionnaires = User.objects.filter(profil__in=['gestionnaire', 'super_admin'])
        for user in gestionnaires:
            Notification.objects.create(
                user=user,
                type='maintenance',
                action='updated',
                title='Appartement en maintenance',
                message=f'Appartement {appartement.numero} mis en maintenance',
                actor=actor,
                url=reverse('appartements:detail', kwargs={'pk': appartement.pk}),
                object_type='appartement',
                object_id=appartement.pk
            )
    
    @staticmethod
    def notify_facture_created(facture, actor):
        """Notification création facture"""
        from apps.users.models import User
        gestionnaires = User.objects.filter(profil__in=['gestionnaire', 'super_admin'])
        
        for user in gestionnaires:
            if user != actor:
                Notification.objects.create(
                    user=user,
                    type='facturation',
                    action='created',
                    title='Nouvelle facture générée',
                    message=f'{actor.first_name or actor.username} a généré la facture {facture.numero_facture} pour {facture.reservation.client.nom}',
                    actor=actor,
                    url=reverse('facturation:apercu', kwargs={'pk': facture.pk}),
                    url_text='Voir la facture',
                    object_type='facture',
                    object_id=facture.pk,
                    object_name=f'Facture {facture.numero_facture}'
                )