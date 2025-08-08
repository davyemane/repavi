# ==========================================
# apps/reservations/services.py - Services réservations
# ==========================================
from datetime import timedelta, date
from django.core.exceptions import ValidationError

class ReservationService:
    """Service pour la logique métier des réservations selon cahier"""
    
    @staticmethod
    def creer_echeancier(reservation):
        """Créer l'échéancier de paiement automatique selon cahier"""
        from apps.paiements.models import EcheancierPaiement
        
        # Supprimer ancien échéancier si modification
        EcheancierPaiement.objects.filter(reservation=reservation).delete()
        
        # Acompte (40% selon cahier)
        acompte = reservation.prix_total * 0.4
        EcheancierPaiement.objects.create(
            reservation=reservation,
            type_paiement='acompte',
            montant_prevu=acompte,
            date_echeance=reservation.date_arrivee - timedelta(days=7)
        )
        
        # Solde (60% selon cahier)
        solde = reservation.prix_total - acompte
        EcheancierPaiement.objects.create(
            reservation=reservation,
            type_paiement='solde',
            montant_prevu=solde,
            date_echeance=reservation.date_arrivee
        )
    
    @staticmethod
    def verifier_conflits(appartement, date_arrivee, date_depart, reservation_id=None):
        """Vérifier les conflits de dates selon cahier"""
        from .models import Reservation
        
        conflits = Reservation.objects.filter(
            appartement=appartement,
            statut__in=['confirmee', 'en_cours'],
            date_arrivee__lt=date_depart,
            date_depart__gt=date_arrivee
        )
        
        if reservation_id:
            conflits = conflits.exclude(pk=reservation_id)
        
        return conflits.exists()
    
    @staticmethod
    def changer_statut_automatique():
        """Changement automatique des statuts selon cahier"""
        from .models import Reservation
        aujourd_hui = date.today()
        
        # Confirmée → En cours (jour d'arrivée)
        Reservation.objects.filter(
            statut='confirmee',
            date_arrivee=aujourd_hui
        ).update(statut='en_cours')
        
        # En cours → Terminée (jour de départ)
        Reservation.objects.filter(
            statut='en_cours',
            date_depart=aujourd_hui
        ).update(statut='terminee')
        
        # Mettre à jour les statuts d'appartements
        ReservationService.mettre_a_jour_appartements()
    
    @staticmethod
    def mettre_a_jour_appartements():
        """Mettre à jour les statuts d'appartements selon réservations"""
        from apps.appartements.models import Appartement
        from .models import Reservation
        aujourd_hui = date.today()
        
        appartements = Appartement.objects.all()
        
        for appartement in appartements:
            # Vérifier si occupé aujourd'hui
            reservation_active = Reservation.objects.filter(
                appartement=appartement,
                statut='en_cours',
                date_arrivee__lte=aujourd_hui,
                date_depart__gt=aujourd_hui
            ).exists()
            
            if reservation_active:
                appartement.statut = 'occupe'
            else:
                appartement.statut = 'disponible'
            
            appartement.save()
    
    @staticmethod
    def calculer_taux_occupation(appartement=None, mois=None, annee=None):
        """Calculer le taux d'occupation selon cahier"""
        from .models import Reservation
        import calendar
        
        if not mois:
            mois = date.today().month
        if not annee:
            annee = date.today().year
        
        # Nombre de jours dans le mois
        jours_mois = calendar.monthrange(annee, mois)[1]
        
        reservations = Reservation.objects.filter(
            statut__in=['confirmee', 'en_cours', 'terminee'],
            date_arrivee__year=annee,
            date_arrivee__month=mois
        )
        
        if appartement:
            reservations = reservations.filter(appartement=appartement)
            nuits_occupees = sum(r.nombre_nuits for r in reservations)
            return round((nuits_occupees / jours_mois) * 100, 1)
        else:
            # Taux global
            from apps.appartements.models import Appartement
            nb_appartements = Appartement.objects.count()
            nuits_totales = nb_appartements * jours_mois
            nuits_occupees = sum(r.nombre_nuits for r in reservations)
            return round((nuits_occupees / nuits_totales) * 100, 1)
    
    @staticmethod
    def generer_rapport_mensuel(mois=None, annee=None):
        """Générer rapport mensuel selon cahier"""
        from .models import Reservation
        from apps.appartements.models import Appartement
        
        if not mois:
            mois = date.today().month
        if not annee:
            annee = date.today().year
        
        reservations = Reservation.objects.filter(
            date_arrivee__year=annee,
            date_arrivee__month=mois
        ).select_related('client', 'appartement')
        
        rapport = {
            'mois': mois,
            'annee': annee,
            'total_reservations': reservations.count(),
            'revenus_total': sum(r.prix_total for r in reservations if r.statut != 'annulee'),
            'taux_occupation': ReservationService.calculer_taux_occupation(None, mois, annee),
            'nouvelles_reservations': reservations.filter(statut='confirmee').count(),
            'reservations_terminees': reservations.filter(statut='terminee').count(),
            'reservations_annulees': reservations.filter(statut='annulee').count(),
        }
        
        return rapport