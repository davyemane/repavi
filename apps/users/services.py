# ==========================================
# apps/users/services.py - Services métier pour les utilisateurs
# ==========================================
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from calendar import monthrange
from typing import Dict, Any, List
from .models import User

class DashboardService:
    """
    Service pour les données du dashboard selon cahier des charges
    """
    
    @staticmethod
    def get_kpis_principaux() -> Dict[str, Any]:
        """
        Récupère les KPIs principaux selon le cahier des charges
        """
        # Import ici pour éviter les imports circulaires
        from apps.appartements.models import Appartement
        from apps.clients.models import Client
        from apps.reservations.models import Reservation
        from apps.paiements.models import EcheancierPaiement
        from apps.inventaire.models import EquipementAppartement
        from apps.menage.models import TacheMenage
        
        now = timezone.now()
        today = now.date()
        premier_mois = today.replace(day=1)
        
        return {
            # Appartements
            'total_appartements': Appartement.objects.count(),
            'appartements_disponibles': Appartement.objects.filter(statut='disponible').count(),
            'appartements_occupes': Appartement.objects.filter(statut='occupe').count(),
            
            # Clients
            'total_clients': Client.objects.count(),
            'nouveaux_clients_mois': Client.objects.filter(date_creation__gte=premier_mois).count(),
            
            # Réservations
            'reservations_actives': Reservation.objects.filter(
                statut__in=['confirmee', 'en_cours'],
                date_arrivee__lte=today,
                date_depart__gt=today
            ).count(),
            'reservations_ce_mois': Reservation.objects.filter(
                date_arrivee__year=today.year,
                date_arrivee__month=today.month
            ).count(),
            'reservations_aujourd_hui': Reservation.objects.filter(date_arrivee=today).count(),
            'arrivees_aujourd_hui': Reservation.objects.filter(date_arrivee=today).select_related('client', 'appartement'),
            
            # Paiements
            'paiements_en_attente': EcheancierPaiement.objects.filter(statut='en_attente').count(),
            'paiements_retard': EcheancierPaiement.objects.filter(
                statut='en_attente',
                date_echeance__lt=today
            ).count(),
            
            # Inventaire
            'total_equipements': EquipementAppartement.objects.count(),
            'equipements_defectueux': EquipementAppartement.objects.filter(
                etat__in=['defectueux', 'hors_service']
            ).count(),
            
            # Ménage
            'taches_menage_urgentes': TacheMenage.objects.filter(
                statut='a_faire',
                date_prevue__lte=today
            ).count(),
            
            # Métadonnées
            'mois_actuel': today,
        }
    
    @staticmethod
    def get_revenus_mois(annee: int, mois: int) -> float:
        """
        Calcul simple des revenus selon cahier des charges
        """
        try:
            from apps.comptabilite.models import ComptabiliteAppartement
            revenus = ComptabiliteAppartement.objects.filter(
                type_mouvement='revenu',
                date_mouvement__year=annee,
                date_mouvement__month=mois
            ).aggregate(total=Sum('montant'))['total']
            return float(revenus) if revenus else 0.0
        except ImportError:
            # Si le modèle n'existe pas encore, calculer à partir des réservations
            from apps.reservations.models import Reservation
            reservations = Reservation.objects.filter(
                statut__in=['confirmee', 'en_cours', 'terminee'],
                date_arrivee__year=annee,
                date_arrivee__month=mois
            ).aggregate(total=Sum('montant_total'))['total']
            return float(reservations) if reservations else 0.0
    
    @staticmethod
    def get_taux_occupation_mois(annee: int, mois: int) -> int:
        """
        Calcul simple du taux d'occupation selon cahier des charges
        """
        from apps.appartements.models import Appartement
        from apps.reservations.models import Reservation
        
        total_appartements = Appartement.objects.count()
        if total_appartements == 0:
            return 0
            
        jours_mois = monthrange(annee, mois)[1]
        nuits_totales_possibles = total_appartements * jours_mois
        
        # Compter les nuits réellement occupées
        nuits_occupees = 0
        for reservation in Reservation.objects.filter(
            statut__in=['confirmee', 'en_cours', 'terminee'],
            date_arrivee__year=annee,
            date_arrivee__month=mois
        ).select_related('appartement'):
            # Intersection avec le mois
            debut_mois = datetime(annee, mois, 1).date()
            fin_mois = datetime(annee, mois, jours_mois).date()
            
            debut_sejour = max(reservation.date_arrivee, debut_mois)
            fin_sejour = min(reservation.date_depart, fin_mois)
            
            if debut_sejour < fin_sejour:
                nuits_occupees += (fin_sejour - debut_sejour).days
        
        return round((nuits_occupees / nuits_totales_possibles) * 100) if nuits_totales_possibles > 0 else 0


class PermissionsService:
    """
    Service pour la gestion des permissions selon cahier des charges
    """
    
    @staticmethod
    def can_manage_gestionnaires(user: User) -> bool:
        """
        Seuls les Super Admin peuvent gérer les gestionnaires selon cahier
        """
        return user.is_authenticated and user.profil == 'super_admin'
    
    @staticmethod
    def can_access_dashboard(user: User) -> bool:
        """
        Gestionnaires et Super Admin peuvent accéder au dashboard selon cahier
        """
        return user.is_authenticated and user.profil in ['gestionnaire', 'super_admin']
    
    @staticmethod
    def get_permissions_matrix(user: User) -> Dict[str, bool]:
        """
        Matrice des permissions selon le cahier des charges
        """
        if not user.is_authenticated:
            return {}
        
        if user.profil == 'super_admin':
            return {
                'gestion_appartements': True,
                'gestion_clients': True,
                'reservations': True,
                'paiements': True,
                'inventaire': True,
                'comptabilite': True,
                'menage': True,
                'facturation': True,
                'rapports': True,
                'gestion_gestionnaires': True,  # Seul le super admin
            }
        elif user.profil == 'gestionnaire':
            return {
                'gestion_appartements': True,
                'gestion_clients': True,
                'reservations': True,
                'paiements': True,
                'inventaire': True,
                'comptabilite': True,
                'menage': True,
                'facturation': True,
                'rapports': True,
                'gestion_gestionnaires': False,  # Pas de gestion d'autres gestionnaires
            }
        else:
            return {}


class GestionnaireService:
    """
    Service pour la gestion des gestionnaires
    """
    
    @staticmethod
    def get_stats_gestionnaires() -> Dict[str, int]:
        """
        Statistiques des gestionnaires pour l'interface Super Admin
        """
        return {
            'total_gestionnaires': User.objects.filter(profil='gestionnaire').count(),
            'gestionnaires_actifs': User.objects.filter(
                profil='gestionnaire', 
                is_active=True
            ).count(),
            'gestionnaires_inactifs': User.objects.filter(
                profil='gestionnaire', 
                is_active=False
            ).count(),
            'super_admins': User.objects.filter(profil='super_admin').count(),
            'nouveaux_ce_mois': User.objects.filter(
                profil='gestionnaire',
                date_joined__gte=timezone.now().replace(day=1)
            ).count(),
        }
    
    @staticmethod
    def search_gestionnaires(search_term: str = '', statut: str = '') -> List[User]:
        """
        Recherche et filtrage des gestionnaires
        """
        queryset = User.objects.filter(
            profil__in=['gestionnaire', 'super_admin']
        ).order_by('-date_joined')
        
        if search_term:
            queryset = queryset.filter(
                Q(username__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(first_name__icontains=search_term) |
                Q(last_name__icontains=search_term)
            )
        
        if statut == 'actif':
            queryset = queryset.filter(is_active=True)
        elif statut == 'inactif':
            queryset = queryset.filter(is_active=False)
            
        return list(queryset.select_related())
    
    @staticmethod
    def can_modify_gestionnaire(current_user: User, target_user: User) -> bool:
        """
        Vérifier si l'utilisateur actuel peut modifier le gestionnaire cible
        """
        # Seuls les Super Admin peuvent modifier les gestionnaires
        if not PermissionsService.can_manage_gestionnaires(current_user):
            return False
        
        # Un gestionnaire ne peut pas se désactiver lui-même
        if current_user == target_user:
            return False
            
        # Seuls les gestionnaires et super admins peuvent être modifiés
        return target_user.profil in ['gestionnaire', 'super_admin']


class HistoriqueService:
    """
    Service pour l'historique des activités selon cahier des charges
    """
    
    @staticmethod
    def get_activites_recentes(limite: int = 50) -> Dict[str, Any]:
        """
        Récupère les activités récentes du système
        """
        from apps.reservations.models import Reservation
        
        # Pour l'instant, on se base sur les réservations
        # À étendre avec d'autres types d'activités selon les besoins
        reservations = Reservation.objects.select_related(
            'client', 'appartement'
        ).order_by('-date_creation')[:limite]
        
        today = timezone.now().date()
        
        return {
            'reservations': reservations,
            'stats_jour': {
                'reservations_aujourd_hui': Reservation.objects.filter(
                    date_creation__date=today
                ).count(),
                # À compléter avec les autres modèles
            }
        }
    
    @staticmethod
    def get_actions_utilisateur(user: User, limite: int = 20) -> List[Dict[str, Any]]:
        """
        Récupère les dernières actions d'un utilisateur spécifique
        """
        # À implémenter selon les besoins avec un système de logs
        # Pour l'instant, retourne une liste vide
        return []


class ValidationService:
    """
    Service pour les validations métier selon cahier des charges
    """
    
    @staticmethod
    def validate_creation_gestionnaire(data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Valide les données de création d'un gestionnaire
        """
        errors = {}
        
        # Vérifier l'unicité du nom d'utilisateur
        if data.get('username'):
            if User.objects.filter(username=data['username']).exists():
                errors['username'] = ['Ce nom d\'utilisateur existe déjà.']
        
        # Vérifier l'unicité de l'email
        if data.get('email'):
            if User.objects.filter(email=data['email']).exists():
                errors['email'] = ['Cet email est déjà utilisé.']
        
        # Valider le profil
        if data.get('profil') not in ['gestionnaire', 'super_admin']:
            errors['profil'] = ['Profil invalide.']
        
        return errors
    
    @staticmethod
    def can_delete_gestionnaire(gestionnaire: User, current_user: User) -> tuple[bool, str]:
        """
        Vérifier si un gestionnaire peut être supprimé
        """
        # Empêcher la suppression de son propre compte
        if gestionnaire == current_user:
            return False, "Vous ne pouvez pas supprimer votre propre compte."
        
        # Vérifier s'il y a des données liées (à implémenter selon les modèles)
        # Pour l'instant, on autorise la désactivation plutôt que la suppression
        return False, "La suppression n'est pas autorisée. Utilisez la désactivation."