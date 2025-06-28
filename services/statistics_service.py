# services/statistics_service.py
from django.db.models import Count, Sum, Q, Avg
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from reservations.models import Maison, Reservation

User = get_user_model()

class StatisticsService:
    """Service pour les statistiques du dashboard"""
    
    @staticmethod
    def get_dashboard_stats(user):
        """Récupère les statistiques pour le dashboard selon les permissions"""
        stats = {}
        
        try:
            if hasattr(user, 'is_super_admin') and user.is_super_admin():
                # Statistiques globales pour super admin
                stats = StatisticsService._get_global_stats()
            else:
                # Statistiques pour gestionnaire
                stats = StatisticsService._get_gestionnaire_stats(user)
            
            # Ajouter le calcul du CA
            stats.update(StatisticsService._get_revenue_stats(user))
            
        except Exception as e:
            print(f"Erreur service statistiques: {e}")
            # Retourner des stats vides en cas d'erreur
            stats = StatisticsService._get_empty_stats()
        
        return stats
    
    @staticmethod
    def _get_global_stats():
        """Statistiques globales pour super admin"""
        return {
            'total_maisons': Maison.objects.count(),
            'maisons_disponibles': Maison.objects.filter(disponible=True).count(),
            'maisons_featured': Maison.objects.filter(featured=True).count(),
            'total_reservations': Reservation.objects.count(),
            'reservations_en_attente': Reservation.objects.filter(statut='en_attente').count(),
            'reservations_confirmees': Reservation.objects.filter(statut='confirmee').count(),
            'total_users': User.objects.count(),
            'users_actifs': User.objects.filter(is_active=True).count(),
            'total_clients': User.objects.filter(role='CLIENT').count() if hasattr(User, 'role') else User.objects.filter(is_staff=False).count(),
            'total_gestionnaires': User.objects.filter(role='GESTIONNAIRE').count() if hasattr(User, 'role') else User.objects.filter(is_staff=True, is_superuser=False).count(),
            'total_admins': User.objects.filter(role='SUPER_ADMIN').count() if hasattr(User, 'role') else User.objects.filter(is_superuser=True).count(),
        }
    
    @staticmethod
    def _get_gestionnaire_stats(user):
        """Statistiques pour un gestionnaire spécifique"""
        maisons_user = Maison.objects.filter(gestionnaire=user)
        reservations_user = Reservation.objects.filter(maison__gestionnaire=user)
        
        return {
            'total_maisons': maisons_user.count(),
            'maisons_disponibles': maisons_user.filter(disponible=True).count(),
            'maisons_featured': maisons_user.filter(featured=True).count(),
            'total_reservations': reservations_user.count(),
            'reservations_en_attente': reservations_user.filter(statut='en_attente').count(),
            'reservations_confirmees': reservations_user.filter(statut='confirmee').count(),
            # Pas d'accès aux stats utilisateurs pour les gestionnaires
            'total_users': 0,
            'users_actifs': 0,
            'total_clients': 0,
            'total_gestionnaires': 0,
            'total_admins': 0,
        }
    
    @staticmethod
    def _get_revenue_stats(user):
        """Calcul des statistiques de chiffre d'affaires"""
        # Période actuelle (mois en cours)
        debut_mois = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fin_mois_precedent = debut_mois - timedelta(days=1)
        debut_mois_precedent = fin_mois_precedent.replace(day=1)
        
        # Requêtes de base
        ca_query = Reservation.objects.filter(
            date_creation__gte=debut_mois,
            statut='confirmee'
        )
        
        ca_precedent_query = Reservation.objects.filter(
            date_creation__gte=debut_mois_precedent,
            date_creation__lt=debut_mois,
            statut='confirmee'
        )
        
        # Filtrer selon les permissions
        if not (hasattr(user, 'is_super_admin') and user.is_super_admin()):
            ca_query = ca_query.filter(maison__gestionnaire=user)
            ca_precedent_query = ca_precedent_query.filter(maison__gestionnaire=user)
        
        # Calculs
        ca_mensuel = ca_query.aggregate(total=Sum('prix_total'))['total'] or 0
        ca_precedent = ca_precedent_query.aggregate(total=Sum('prix_total'))['total'] or 0
        
        # Évolution
        if ca_precedent > 0:
            evolution_ca = round(((ca_mensuel - ca_precedent) / ca_precedent) * 100, 1)
        else:
            evolution_ca = 100 if ca_mensuel > 0 else 0
        
        return {
            'ca_mensuel': ca_mensuel,
            'ca_precedent': ca_precedent,
            'evolution_ca': evolution_ca,
        }
    
    @staticmethod
    def _get_empty_stats():
        """Statistiques vides en cas d'erreur"""
        return {
            'total_maisons': 0,
            'maisons_disponibles': 0,
            'maisons_featured': 0,
            'total_reservations': 0,
            'reservations_en_attente': 0,
            'reservations_confirmees': 0,
            'total_users': 0,
            'users_actifs': 0,
            'total_clients': 0,
            'total_gestionnaires': 0,
            'total_admins': 0,
            'ca_mensuel': 0,
            'ca_precedent': 0,
            'evolution_ca': 0,
        }
    
    @staticmethod
    def get_maisons_populaires(user, limit=5):
        """Récupère les maisons les plus populaires"""
        try:
            if hasattr(user, 'is_super_admin') and user.is_super_admin():
                maisons = Maison.objects.all()
            else:
                maisons = Maison.objects.filter(gestionnaire=user)
            
            return maisons.annotate(
                nb_reservations=Count('reservations')
            ).order_by('-nb_reservations')[:limit]
            
        except Exception:
            return Maison.objects.none()
    
    @staticmethod
    def get_revenue_by_period(user, period='month'):
        """Calcule le chiffre d'affaires par période"""
        try:
            now = datetime.now()
            
            if period == 'month':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == 'week':
                start_date = now - timedelta(days=now.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'year':
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            reservations = Reservation.objects.filter(
                date_creation__gte=start_date,
                statut='confirmee'
            )
            
            if not (hasattr(user, 'is_super_admin') and user.is_super_admin()):
                reservations = reservations.filter(maison__gestionnaire=user)
            
            return reservations.aggregate(total=Sum('prix_total'))['total'] or 0
            
        except Exception:
            return 0
    
    @staticmethod
    def get_occupancy_rate(user):
        """Calcule le taux d'occupation"""
        try:
            if hasattr(user, 'is_super_admin') and user.is_super_admin():
                maisons = Maison.objects.all()
            else:
                maisons = Maison.objects.filter(gestionnaire=user)
            
            total_maisons = maisons.count()
            if total_maisons == 0:
                return 0
            
            # Maisons ayant des réservations ce mois
            debut_mois = datetime.now().replace(day=1)
            maisons_occupees = maisons.filter(
                reservations__date_debut__lte=datetime.now(),
                reservations__date_fin__gte=debut_mois,
                reservations__statut__in=['confirmee', 'terminee']
            ).distinct().count()
            
            return round((maisons_occupees / total_maisons) * 100, 1)
            
        except Exception:
            return 0