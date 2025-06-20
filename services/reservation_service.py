# services/reservation_service.py
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from home.models import Reservation


class ReservationService:
    """Service pour la gestion des réservations"""
    
    @staticmethod
    def create_reservation(client, maison, data):
        """Créer une nouvelle réservation"""
        if not client.is_client():
            raise PermissionDenied("Seuls les clients peuvent faire des réservations")
        
        # Vérifier la disponibilité
        if not ReservationService.is_available(maison, data['date_debut'], data['date_fin']):
            raise ValidationError("Ces dates ne sont pas disponibles")
        
        # Calculer le prix total
        duree = (data['date_fin'] - data['date_debut']).days
        prix_total = duree * maison.prix_par_nuit
        
        with transaction.atomic():
            reservation = Reservation.objects.create(
                maison=maison,
                client=client,
                date_debut=data['date_debut'],
                date_fin=data['date_fin'],
                nombre_personnes=data['nombre_personnes'],
                prix_total=prix_total,
                telephone=data.get('telephone', client.telephone),
                message=data.get('message', ''),
                statut='en_attente'
            )
            
            # TODO: Envoyer notification au gestionnaire
            # NotificationService.notify_new_reservation(reservation)
            
            return reservation
    
    @staticmethod
    def update_reservation_status(user, reservation, nouveau_statut):
        """Mettre à jour le statut d'une réservation"""
        if not reservation.can_be_managed_by(user):
            raise PermissionDenied("Vous n'avez pas les droits pour modifier cette réservation")
        
        old_status = reservation.statut
        reservation.statut = nouveau_statut
        reservation.save()
        
        # TODO: Notifications selon le changement de statut
        # NotificationService.notify_status_change(reservation, old_status, nouveau_statut)
        
        return reservation
    
    @staticmethod
    def is_available(maison, date_debut, date_fin):
        """Vérifier la disponibilité d'une maison"""
        if not maison.disponible:
            return False
        
        # Vérifier les conflits avec d'autres réservations
        conflicting_reservations = Reservation.objects.filter(
            maison=maison,
            statut__in=['confirmee', 'en_attente'],
            date_debut__lt=date_fin,
            date_fin__gt=date_debut
        )
        
        return not conflicting_reservations.exists()
    
    @staticmethod
    def get_reservations_for_user(user):
        """Récupérer les réservations selon le rôle utilisateur"""
        if user.is_client():
            return Reservation.objects.filter(client=user).select_related('maison')
        elif user.is_gestionnaire():
            return Reservation.objects.filter(maison__gestionnaire=user).select_related('maison', 'client')
        elif user.is_super_admin():
            return Reservation.objects.all().select_related('maison', 'client')
        else:
            return Reservation.objects.none()
    
    @staticmethod
    def get_calendar_data(maison, year=None, month=None):
        """Récupérer les données du calendrier pour une maison"""
        if not year:
            year = timezone.now().year
        if not month:
            month = timezone.now().month
        
        # Récupérer les réservations du mois
        start_date = timezone.datetime(year, month, 1).date()
        if month == 12:
            end_date = timezone.datetime(year + 1, 1, 1).date()
        else:
            end_date = timezone.datetime(year, month + 1, 1).date()
        
        reservations = Reservation.objects.filter(
            maison=maison,
            statut__in=['confirmee', 'en_attente'],
            date_debut__lt=end_date,
            date_fin__gt=start_date
        )
        
        # Formater pour le calendrier frontend
        calendar_data = []
        for reservation in reservations:
            calendar_data.append({
                'start': reservation.date_debut.isoformat(),
                'end': reservation.date_fin.isoformat(),
                'title': f"Réservé - {reservation.client.first_name}",
                'status': reservation.statut,
                'id': reservation.id
            })
        
        return calendar_data