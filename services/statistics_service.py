# services/statistics_service.py
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from home.models import Maison, Reservation

User = get_user_model()


class StatisticsService:
    """Service pour les statistiques"""
    
    @staticmethod
    def get_dashboard_stats(user):
        """Récupérer les statistiques pour le dashboard"""
        if user.is_gestionnaire():
            return StatisticsService._get_gestionnaire_stats(user)
        elif user.is_super_admin():
            return StatisticsService._get_super_admin_stats()
        else:
            return {}
    
    @staticmethod
    def _get_gestionnaire_stats(gestionnaire):
        """Statistiques pour un gestionnaire"""
        today = timezone.now().date()
        start_month = today.replace(day=1)
        start_year = today.replace(month=1, day=1)
        
        maisons = Maison.objects.filter(gestionnaire=gestionnaire)
        reservations = Reservation.objects.filter(maison__gestionnaire=gestionnaire)
        
        return {
            'maisons_count': maisons.count(),
            'maisons_disponibles': maisons.filter(disponible=True).count(),
            'reservations_mois': reservations.filter(
                date_creation__gte=start_month,
                statut='confirmee'
            ).count(),
            'chiffre_affaires_mois': reservations.filter(
                date_creation__gte=start_month,
                statut='confirmee'
            ).aggregate(total=Sum('prix_total'))['total'] or 0,
            'chiffre_affaires_annee': reservations.filter(
                date_creation__gte=start_year,
                statut='confirmee'
            ).aggregate(total=Sum('prix_total'))['total'] or 0,
            'reservations_en_attente': reservations.filter(statut='en_attente').count(),
            'taux_occupation': StatisticsService._calculate_occupation_rate(maisons, today.month),
        }
    
    @staticmethod
    def _get_super_admin_stats():
        """Statistiques globales pour super admin"""
        today = timezone.now().date()
        start_month = today.replace(day=1)
        
        return {
            'total_utilisateurs': User.objects.count(),
            'total_clients': User.objects.filter(role='CLIENT').count(),
            'total_gestionnaires': User.objects.filter(role='GESTIONNAIRE').count(),
            'total_maisons': Maison.objects.count(),
            'maisons_actives': Maison.objects.filter(disponible=True).count(),
            'reservations_mois': Reservation.objects.filter(
                date_creation__gte=start_month
            ).count(),
            'chiffre_affaires_mois': Reservation.objects.filter(
                date_creation__gte=start_month,
                statut='confirmee'
            ).aggregate(total=Sum('prix_total'))['total'] or 0,
        }
    
    @staticmethod
    def _calculate_occupation_rate(maisons, month):
        """Calculer le taux d'occupation"""
        if not maisons.exists():
            return 0
        
        # Logique simplifiée - à améliorer selon les besoins
        total_days = 30  # Approximation
        reserved_days = 0
        
        for maison in maisons:
            reservations = Reservation.objects.filter(
                maison=maison,
                statut='confirmee',
                date_debut__month=month
            )
            for reservation in reservations:
                reserved_days += reservation.duree_sejour
        
        max_possible_days = total_days * maisons.count()
        return (reserved_days / max_possible_days * 100) if max_possible_days > 0 else 0