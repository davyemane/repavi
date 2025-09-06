# ==========================================
# services/reservation_service.py - Services métier pour les réservations CORRIGÉ
# ==========================================

from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

# from reservations.models import Reservation, Paiement, TypePaiement, Disponibilite
# from home.models import Maison


class ReservationService:
    """Service de gestion des réservations"""
    
    @staticmethod
    def get_reservations_for_user(user):
        """Récupère les réservations selon le type d'utilisateur"""
        if user.is_anonymous:
            from apps.reservations.models import Reservation
            return Reservation.objects.none()
        
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            from apps.reservations.models import Reservation
            return Reservation.objects.all()
        elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
            from apps.reservations.models import Reservation
            return Reservation.objects.filter(appartement__gestionnaire=user)
        elif hasattr(user, 'is_client') and user.is_client():
            from apps.reservations.models import Reservation
            return Reservation.objects.filter(client=user)
        
        from apps.reservations.models import Reservation
        return Reservation.objects.none()
    
    @staticmethod
    def verifier_disponibilite_periode(appartement, date_debut: date, date_fin: date, 
                                       exclude_reservation_id: Optional[int] = None) -> bool:
        """Vérifie la disponibilité d'un appartement pour une période"""
        from apps.reservations.models import Reservation
        
        conflits = Reservation.objects.filter(
            appartement=appartement,
            statut__in=['confirmee', 'en_cours'],
            date_arrivee__lt=date_fin,
            date_depart__gt=date_debut
        )
        
        if exclude_reservation_id:
            conflits = conflits.exclude(pk=exclude_reservation_id)
            
        return not conflits.exists()
    
    @staticmethod
    def calculer_prix_reservation(appartement, date_debut: date, date_fin: date, 
                                  nombre_personnes: int = 1, reduction: Decimal = 0) -> Dict:
        """Calcule le prix total d'une réservation"""
        nombre_nuits = (date_fin - date_debut).days
        
        if nombre_nuits <= 0:
            raise ValidationError("La durée du séjour doit être d'au moins 1 nuit.")
        
        # Prix de base
        prix_base = nombre_nuits * appartement.prix_par_nuit
        
        # Réductions éventuelles
        prix_reduit = prix_base - reduction
        
        # Frais de service (exemple : 5%)
        frais_service = prix_reduit * Decimal('0.05')
        
        # Prix total
        prix_total = prix_reduit + frais_service
        
        return {
            'nombre_nuits': nombre_nuits,
            'prix_par_nuit': appartement.prix_par_nuit,
            'prix_base': prix_base,
            'reduction': reduction,
            'frais_service': frais_service,
            'prix_total': prix_total
        }
    
    @staticmethod
    def creer_reservation(client, appartement, date_debut: date, date_fin: date, 
                         nombre_personnes: int = 1, **kwargs):
        """Crée une nouvelle réservation"""
        
        # Validations
        if nombre_personnes <= 0:
            raise ValidationError("Le nombre de personnes doit être positif.")
        
        # Vérifier la disponibilité
        if not ReservationService.verifier_disponibilite_periode(appartement, date_debut, date_fin):
            raise ValidationError("Cet appartement n'est pas disponible pour ces dates.")
        
        # Calculer les prix
        calcul_prix = ReservationService.calculer_prix_reservation(
            appartement, date_debut, date_fin, nombre_personnes
        )
        
        # Créer la réservation
        with transaction.atomic():
            from apps.reservations.models import Reservation
            reservation = Reservation.objects.create(
                client=client,
                appartement=appartement,
                date_arrivee=date_debut,
                date_depart=date_fin,
                nombre_personnes=nombre_personnes,
                prix_par_nuit=appartement.prix_par_nuit,
                prix_total=calcul_prix['prix_total'],
                **kwargs
            )
        
        return reservation
    
    @staticmethod
    def confirmer_reservation(reservation, user=None) -> bool:
        """Confirme une réservation"""
        if reservation.statut != 'en_attente':
            raise ValidationError("Seules les réservations en attente peuvent être confirmées.")
        
        # Vérifier à nouveau la disponibilité
        if not ReservationService.verifier_disponibilite_periode(
            reservation.appartement, 
            reservation.date_arrivee, 
            reservation.date_depart,
            reservation.id
        ):
            raise ValidationError("Cet appartement n'est plus disponible pour ces dates.")
        
        with transaction.atomic():
            reservation.statut = 'confirmee'
            reservation.save()
            
            # Créer l'échéancier de paiement
            ReservationService.creer_echeancier(reservation)
            
            # Notifier le client
            # TODO: Implémenter les notifications
            
        return True
    
    @staticmethod
    def annuler_reservation(reservation, raison: str, user=None) -> bool:
        """Annule une réservation"""
        if reservation.statut not in ['en_attente', 'confirmee']:
            raise ValidationError("Cette réservation ne peut plus être annulée.")
        
        with transaction.atomic():
            reservation.statut = 'annulee'
            reservation.save()
            
            # Supprimer l'échéancier associé
            from apps.paiements.models import EcheancierPaiement
            EcheancierPaiement.objects.filter(reservation=reservation).delete()
            
        return True
    
    @staticmethod
    def creer_echeancier(reservation):
        """Créer l'échéancier de paiement automatique selon cahier"""
        from apps.paiements.models import EcheancierPaiement
        
        # Supprimer ancien échéancier pour éviter les bugs de calcul
        EcheancierPaiement.objects.filter(reservation=reservation).delete()
        
        # Acompte (40% selon cahier)
        acompte = reservation.prix_total * Decimal('0.4')
        EcheancierPaiement.objects.create(
            reservation=reservation,
            type_paiement='acompte',
            montant_prevu=acompte,
            date_echeance=reservation.date_arrivee - timedelta(days=7)
        )
        
        # Solde (60% selon cahier) - CORRECTION : toujours 60%, pas recalcul
        solde = reservation.prix_total * Decimal('0.6')
        EcheancierPaiement.objects.create(
            reservation=reservation,
            type_paiement='solde',
            montant_prevu=solde,
            date_echeance=reservation.date_arrivee
        )
    
    @staticmethod
    def get_prochaines_arrivees(user, nb_jours: int = 7):
        """Récupère les prochaines arrivées"""
        date_limite = timezone.now().date() + timedelta(days=nb_jours)
        
        return ReservationService.get_reservations_for_user(user).filter(
            statut='confirmee',
            date_arrivee__gte=timezone.now().date(),
            date_arrivee__lte=date_limite
        ).order_by('date_arrivee')
    
    @staticmethod
    def get_prochains_departs(user, nb_jours: int = 7):
        """Récupère les prochains départs"""
        date_limite = timezone.now().date() + timedelta(days=nb_jours)
        
        return ReservationService.get_reservations_for_user(user).filter(
            statut='confirmee',
            date_depart__gte=timezone.now().date(),
            date_depart__lte=date_limite
        ).order_by('date_depart')
    
    @staticmethod
    def get_statistiques_reservations(user) -> Dict:
        """Récupère les statistiques des réservations - CORRIGÉ"""
        reservations = ReservationService.get_reservations_for_user(user)
        
        stats = {}
        
        # Statistiques de base
        stats['total_reservations'] = reservations.count()
        stats['reservations_en_attente'] = reservations.filter(statut='en_attente').count()
        stats['reservations_confirmees'] = reservations.filter(statut='confirmee').count()
        stats['reservations_terminees'] = reservations.filter(statut='terminee').count()
        stats['reservations_annulees'] = reservations.filter(statut='annulee').count()
        
        # Revenus - CORRECTIONS avec .get()
        revenus_query = reservations.filter(statut__in=['confirmee', 'terminee'])
        revenus_total_result = revenus_query.aggregate(total=Sum('prix_total'))
        stats['revenus_total'] = revenus_total_result.get('total') or 0
        
        # Revenus du mois courant
        debut_mois = timezone.now().replace(day=1).date()
        revenus_mois_result = revenus_query.filter(
            date_creation__gte=debut_mois
        ).aggregate(total=Sum('prix_total'))
        stats['revenus_mois'] = revenus_mois_result.get('total') or 0
        
        # Moyennes - CORRECTIONS avec .get()
        if stats['total_reservations'] > 0:
            duree_result = reservations.aggregate(moyenne=Avg('nombre_nuits'))
            stats['duree_moyenne'] = duree_result.get('moyenne') or 0
            
            personnes_result = reservations.aggregate(moyenne=Avg('nombre_personnes'))
            stats['personnes_moyenne'] = personnes_result.get('moyenne') or 0
            
            prix_result = reservations.aggregate(moyenne=Avg('prix_total'))
            stats['prix_moyen'] = prix_result.get('moyenne') or 0
        else:
            stats.update({
                'duree_moyenne': 0,
                'personnes_moyenne': 0,
                'prix_moyen': 0
            })
        
        # Prochaines échéances
        stats['arrivees_aujourd_hui'] = reservations.filter(
            statut='confirmee',
            date_arrivee=timezone.now().date()
        ).count()
        
        stats['departs_aujourd_hui'] = reservations.filter(
            statut='confirmee',
            date_depart=timezone.now().date()
        ).count()
        
        return stats
    
    @staticmethod
    def get_evolution_reservations(user, nb_mois: int = 12) -> List[Dict]:
        """Récupère l'évolution des réservations par mois"""
        reservations = ReservationService.get_reservations_for_user(user)
        
        # Calculer les 12 derniers mois
        aujourd_hui = timezone.now().date()
        mois_data = []
        
        for i in range(nb_mois):
            # Calcul du mois
            if aujourd_hui.month - i > 0:
                mois = aujourd_hui.month - i
                annee = aujourd_hui.year
            else:
                mois = 12 + (aujourd_hui.month - i)
                annee = aujourd_hui.year - 1
            
            # Réservations du mois
            reservations_mois = reservations.filter(
                date_creation__year=annee,
                date_creation__month=mois
            )
            
            # CORRECTION avec .get()
            revenus_result = reservations_mois.filter(
                statut__in=['confirmee', 'terminee']
            ).aggregate(total=Sum('prix_total'))
            
            mois_data.append({
                'mois': f"{annee}-{mois:02d}",
                'reservations': reservations_mois.count(),
                'revenus': revenus_result.get('total') or 0
            })
        
        return list(reversed(mois_data))


class PaiementService:
    """Service de gestion des paiements - CORRIGÉ"""
    
    @staticmethod
    def valider_paiement_echeance(paiement_id: int, reference_externe: str = None,
                                 notes: str = None) -> bool:
        """Valide un paiement d'échéance"""
        from apps.paiements.models import EcheancierPaiement
        
        paiement = EcheancierPaiement.objects.get(pk=paiement_id)
        
        # Marquer comme payé
        paiement.statut = 'paye'
        paiement.date_paiement = timezone.now().date()
        paiement.save()
        
        # CORRECTION : Utiliser .get() au lieu d'accès direct
        montant_total_result = paiement.reservation.echeanciers.filter(
            statut='paye'
        ).aggregate(total=Sum('montant_paye'))
        
        montant_total_paye = montant_total_result.get('total') or 0
        
        # Vérifier si la réservation est entièrement payée
        if montant_total_paye >= paiement.reservation.prix_total:
            # TODO: Déclencher des actions si entièrement payé
            pass
        
        return True
    
    @staticmethod
    def get_statistiques_paiements(user, date_debut: date = None, 
                                  date_fin: date = None) -> Dict:
        """Récupère les statistiques de paiements - CORRIGÉ"""
        from apps.paiements.models import EcheancierPaiement
        
        paiements = EcheancierPaiement.objects.filter(
            reservation__in=ReservationService.get_reservations_for_user(user)
        )
        
        if date_debut:
            paiements = paiements.filter(date_paiement__gte=date_debut)
        if date_fin:
            paiements = paiements.filter(date_paiement__lte=date_fin)
        
        # CORRECTIONS : Utiliser .get() au lieu d'accès direct
        montant_result = paiements.filter(statut='paye').aggregate(total=Sum('montant_paye'))
        
        return {
            'total_paiements': paiements.count(),
            'paiements_payes': paiements.filter(statut='paye').count(),
            'paiements_en_attente': paiements.filter(statut='en_attente').count(),
            'montant_total': montant_result.get('total') or 0,
        }