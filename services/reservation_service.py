# services/reservation_service.py - Services métier pour les réservations

from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from reservations.models import Reservation, Paiement, TypePaiement, Disponibilite
from home.models import Maison


class ReservationService:
    """Service de gestion des réservations"""
    
    @staticmethod
    def get_reservations_for_user(user):
        """Récupère les réservations selon le type d'utilisateur"""
        if user.is_anonymous:
            return Reservation.objects.none()
        
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            return Reservation.objects.all()
        elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
            return Reservation.objects.filter(maison__gestionnaire=user)
        elif hasattr(user, 'is_client') and user.is_client():
            return Reservation.objects.filter(client=user)
        
        return Reservation.objects.none()
    
    @staticmethod
    def verifier_disponibilite_periode(maison: Maison, date_debut: date, date_fin: date, 
                                       exclude_reservation_id: Optional[int] = None) -> bool:
        """Vérifie la disponibilité d'une maison pour une période"""
        return Reservation.objects.verifier_disponibilite(
            maison, date_debut, date_fin, exclude_reservation_id
        )
    
    @staticmethod
    def calculer_prix_reservation(maison: Maison, date_debut: date, date_fin: date, 
                                  nombre_personnes: int = 1, reduction: Decimal = 0) -> Dict:
        """Calcule le prix total d'une réservation"""
        nombre_nuits = (date_fin - date_debut).days
        
        if nombre_nuits <= 0:
            raise ValidationError("La durée du séjour doit être d'au moins 1 nuit.")
        
        # Prix de base
        prix_base = maison.prix_par_nuit * nombre_nuits
        
        # Vérifier s'il y a des prix spéciaux
        disponibilites = Disponibilite.objects.filter(
            maison=maison,
            date__gte=date_debut,
            date__lt=date_fin,
            prix_special__isnull=False
        )
        
        # Calculer avec prix spéciaux si disponibles
        if disponibilites.exists():
            prix_total_special = 0
            date_courante = date_debut
            
            while date_courante < date_fin:
                dispo = disponibilites.filter(date=date_courante).first()
                prix_jour = dispo.prix_special if dispo else maison.prix_par_nuit
                prix_total_special += prix_jour
                date_courante += timedelta(days=1)
            
            prix_base = prix_total_special
        
        # Frais de service (5% par défaut)
        frais_service = prix_base * Decimal('0.05')
        
        # Réductions
        montant_reduction = min(reduction, prix_base)
        
        # Sous-total après réduction
        sous_total = prix_base - montant_reduction
        
        # Total final
        prix_total = sous_total + frais_service
        
        # Acompte (30% du total)
        montant_acompte = prix_total * Decimal('0.30')
        
        return {
            'nombre_nuits': nombre_nuits,
            'prix_par_nuit': maison.prix_par_nuit,
            'prix_base': prix_base,
            'frais_service': frais_service,
            'montant_reduction': montant_reduction,
            'sous_total': sous_total,
            'prix_total': prix_total,
            'montant_acompte': montant_acompte.quantize(Decimal('0.01')),
            'prix_par_personne': prix_total / nombre_personnes,
            'tva': Decimal('0'),  # À implémenter si nécessaire
        }
    
    @staticmethod
    def creer_reservation(client, maison: Maison, date_debut: date, date_fin: date,
                         nombre_personnes: int, **kwargs) -> Reservation:
        """Crée une nouvelle réservation avec validation"""
        
        # Vérifications préalables
        if not maison.disponible:
            raise ValidationError("Cette maison n'est pas disponible à la réservation.")
        
        if nombre_personnes > maison.capacite_personnes:
            raise ValidationError(
                f"Le nombre de personnes ({nombre_personnes}) dépasse "
                f"la capacité de la maison ({maison.capacite_personnes})."
            )
        
        # Vérifier la disponibilité
        if not ReservationService.verifier_disponibilite_periode(maison, date_debut, date_fin):
            raise ValidationError("Cette maison n'est pas disponible pour ces dates.")
        
        # Calculer les prix
        calcul_prix = ReservationService.calculer_prix_reservation(
            maison, date_debut, date_fin, nombre_personnes
        )
        
        # Créer la réservation
        with transaction.atomic():
            reservation = Reservation.objects.create(
                client=client,
                maison=maison,
                date_debut=date_debut,
                date_fin=date_fin,
                nombre_personnes=nombre_personnes,
                prix_par_nuit=maison.prix_par_nuit,
                frais_service=calcul_prix['frais_service'],
                **kwargs
            )
            
            # Mettre à jour le statut d'occupation si confirmée
            if reservation.statut == 'confirmee':
                maison.occuper_maison(client, date_fin)
        
        return reservation
    
    @staticmethod
    def confirmer_reservation(reservation: Reservation, user=None) -> bool:
        """Confirme une réservation"""
        if reservation.statut != 'en_attente':
            raise ValidationError("Seules les réservations en attente peuvent être confirmées.")
        
        # Vérifier à nouveau la disponibilité
        if not ReservationService.verifier_disponibilite_periode(
            reservation.maison, 
            reservation.date_debut, 
            reservation.date_fin,
            reservation.id
        ):
            raise ValidationError("Cette maison n'est plus disponible pour ces dates.")
        
        with transaction.atomic():
            reservation.confirmer(user)
            
            # Notifier le client
            # TODO: Implémenter les notifications
            
        return True
    
    @staticmethod
    def annuler_reservation(reservation: Reservation, raison: str, user=None) -> bool:
        """Annule une réservation"""
        if not reservation.est_annulable:
            raise ValidationError("Cette réservation ne peut plus être annulée.")
        
        with transaction.atomic():
            reservation.annuler(raison, user)
            
            # Gérer les remboursements si nécessaire
            # TODO: Implémenter la logique de remboursement
            
            # Notifier les parties concernées
            # TODO: Implémenter les notifications
            
        return True
    
    @staticmethod
    def get_reservations_par_periode(user, date_debut: date, date_fin: date) -> Dict:
        """Récupère les réservations pour une période avec statistiques"""
        reservations = ReservationService.get_reservations_for_user(user).filter(
            date_debut__lte=date_fin,
            date_fin__gte=date_debut
        )
        
        # Statistiques
        stats = {
            'total': reservations.count(),
            'confirmees': reservations.filter(statut='confirmee').count(),
            'en_attente': reservations.filter(statut='en_attente').count(),
            'terminees': reservations.filter(statut='terminee').count(),
            'annulees': reservations.filter(statut='annulee').count(),
            'revenus': reservations.filter(
                statut__in=['confirmee', 'terminee']
            ).aggregate(total=Sum('prix_total'))['total'] or 0,
        }
        
        return {
            'reservations': reservations,
            'stats': stats
        }
    
    @staticmethod
    def get_occupancy_rate(maison: Maison, date_debut: date, date_fin: date) -> float:
        """Calcule le taux d'occupation d'une maison pour une période"""
        nombre_jours = (date_fin - date_debut).days
        if nombre_jours <= 0:
            return 0.0
        
        jours_occupes = Reservation.objects.filter(
            maison=maison,
            date_debut__lt=date_fin,
            date_fin__gt=date_debut,
            statut__in=['confirmee', 'terminee']
        ).count()
        
        return min((jours_occupes / nombre_jours) * 100, 100.0)
    
    @staticmethod
    def get_prochaines_arrivees(user, nb_jours: int = 7) -> List[Reservation]:
        """Récupère les prochaines arrivées"""
        date_limite = timezone.now().date() + timedelta(days=nb_jours)
        
        return ReservationService.get_reservations_for_user(user).filter(
            statut='confirmee',
            date_debut__gte=timezone.now().date(),
            date_debut__lte=date_limite
        ).order_by('date_debut', 'heure_arrivee')
    
    @staticmethod
    def get_prochains_departs(user, nb_jours: int = 7) -> List[Reservation]:
        """Récupère les prochains départs"""
        date_limite = timezone.now().date() + timedelta(days=nb_jours)
        
        return ReservationService.get_reservations_for_user(user).filter(
            statut='confirmee',
            date_fin__gte=timezone.now().date(),
            date_fin__lte=date_limite
        ).order_by('date_fin', 'heure_depart')


class PaiementService:
    """Service de gestion des paiements"""
    
    @staticmethod
    def creer_paiement(reservation: Reservation, type_paiement: TypePaiement, 
                       montant: Decimal, reference_externe: str = "", 
                       notes: str = "") -> Paiement:
        """Crée un nouveau paiement"""
        
        # Vérifications
        if montant <= 0:
            raise ValidationError("Le montant doit être positif.")
        
        if montant > reservation.montant_restant:
            raise ValidationError(
                f"Le montant ({montant}) dépasse le montant restant "
                f"({reservation.montant_restant})."
            )
        
        # Calculer les frais
        frais = type_paiement.calculer_frais(montant)
        
        # Créer le paiement
        paiement = Paiement.objects.create(
            reservation=reservation,
            type_paiement=type_paiement,
            montant=montant,
            frais=frais,
            reference_externe=reference_externe,
            notes=notes
        )
        
        return paiement
    
    @staticmethod
    def valider_paiement(paiement: Paiement, reference_externe: str = "", 
                        notes: str = "") -> bool:
        """Valide un paiement"""
        if paiement.statut == 'valide':
            raise ValidationError("Ce paiement est déjà validé.")
        
        paiement.valider(reference_externe, notes)
        
        # Vérifier si la réservation est entièrement payée
        montant_total_paye = paiement.reservation.paiements.filter(
            statut='valide'
        ).aggregate(total=Sum('montant'))['total'] or 0
        
        # TODO: Déclencher des actions si entièrement payé
        
        return True
    
    @staticmethod
    def get_statistiques_paiements(user, date_debut: date = None, 
                                  date_fin: date = None) -> Dict:
        """Récupère les statistiques de paiements"""
        paiements = Paiement.objects.filter(
            reservation__in=ReservationService.get_reservations_for_user(user)
        )
        
        if date_debut:
            paiements = paiements.filter(date_creation__gte=date_debut)
        if date_fin:
            paiements = paiements.filter(date_creation__lte=date_fin)
        
        return {
            'total_paiements': paiements.count(),
            'paiements_valides': paiements.filter(statut='valide').count(),
            'paiements_en_attente': paiements.filter(statut='en_attente').count(),
            'montant_total': paiements.filter(statut='valide').aggregate(
                total=Sum('montant')
            )['total'] or 0,
            'frais_total': paiements.filter(statut='valide').aggregate(
                total=Sum('frais')
            )['total'] or 0,
        }


class DisponibiliteService:
    """Service de gestion des disponibilités"""
    
    @staticmethod
    def bloquer_periode(maison: Maison, date_debut: date, date_fin: date, 
                       raison: str = "Bloqué") -> int:
        """Bloque une période pour une maison"""
        
        # Vérifier qu'il n'y a pas de réservations confirmées
        reservations_conflits = Reservation.objects.filter(
            maison=maison,
            date_debut__lt=date_fin,
            date_fin__gt=date_debut,
            statut__in=['confirmee', 'terminee']
        )
        
        if reservations_conflits.exists():
            raise ValidationError(
                "Impossible de bloquer : des réservations confirmées existent pour cette période."
            )
        
        return Disponibilite.objects.bloquer_periode(maison, date_debut, date_fin, raison)
    
    @staticmethod
    def liberer_periode(maison: Maison, date_debut: date, date_fin: date) -> int:
        """Libère une période pour une maison"""
        return Disponibilite.objects.liberer_periode(maison, date_debut, date_fin)
    
    @staticmethod
    def definir_prix_special(maison: Maison, date_debut: date, date_fin: date, 
                           prix_special: Decimal) -> int:
        """Définit un prix spécial pour une période"""
        if prix_special <= 0:
            raise ValidationError("Le prix spécial doit être positif.")
        
        count = 0
        date_courante = date_debut
        
        while date_courante <= date_fin:
            disponibilite, created = Disponibilite.objects.update_or_create(
                maison=maison,
                date=date_courante,
                defaults={'prix_special': prix_special}
            )
            count += 1
            date_courante += timedelta(days=1)
        
        return count
    
    @staticmethod
    def get_calendrier_disponibilite(maison: Maison, mois: int, annee: int) -> Dict:
        """Récupère le calendrier de disponibilité pour un mois"""
        import calendar
        
        premier_jour = date(annee, mois, 1)
        dernier_jour = date(annee, mois, calendar.monthrange(annee, mois)[1])
        
        # Récupérer les disponibilités
        disponibilites = Disponibilite.objects.filter(
            maison=maison,
            date__gte=premier_jour,
            date__lte=dernier_jour
        )
        dispo_dict = {d.date: d for d in disponibilites}
        
        # Récupérer les réservations
        reservations = Reservation.objects.filter(
            maison=maison,
            date_debut__lte=dernier_jour,
            date_fin__gte=premier_jour
        ).exclude(statut='annulee')
        
        # Construire le calendrier
        calendrier = []
        date_courante = premier_jour
        
        while date_courante <= dernier_jour:
            # Vérifier s'il y a une réservation
            reservation = None
            for r in reservations:
                if r.date_debut <= date_courante <= r.date_fin:
                    reservation = r
                    break
            
            # Récupérer la disponibilité
            disponibilite = dispo_dict.get(date_courante)
            
            calendrier.append({
                'date': date_courante,
                'disponible': disponibilite.disponible if disponibilite else True,
                'prix_special': disponibilite.prix_special if disponibilite else None,
                'prix_effectif': disponibilite.prix_effectif if disponibilite else maison.prix_par_nuit,
                'raison_indisponibilite': disponibilite.raison_indisponibilite if disponibilite else "",
                'reservation': reservation,
                'est_passe': date_courante < timezone.now().date()
            })
            
            date_courante += timedelta(days=1)
        
        return {
            'calendrier': calendrier,
            'mois': mois,
            'annee': annee,
            'nom_mois': calendar.month_name[mois],
            'maison': maison
        }


class StatistiquesReservationService:
    """Service pour les statistiques de réservations"""
    
    @staticmethod
    def get_dashboard_stats(user) -> Dict:
        """Récupère les statistiques pour le dashboard"""
        reservations = ReservationService.get_reservations_for_user(user)
        
        # Statistiques générales
        stats = {
            'total_reservations': reservations.count(),
            'en_attente': reservations.filter(statut='en_attente').count(),
            'confirmees': reservations.filter(statut='confirmee').count(),
            'terminees': reservations.filter(statut='terminee').count(),
            'annulees': reservations.filter(statut='annulee').count(),
        }
        
        # Revenus
        revenus_query = reservations.filter(statut__in=['confirmee', 'terminee'])
        stats['revenus_total'] = revenus_query.aggregate(
            total=Sum('prix_total')
        )['total'] or 0
        
        # Revenus du mois courant
        debut_mois = timezone.now().replace(day=1).date()
        stats['revenus_mois'] = revenus_query.filter(
            date_creation__gte=debut_mois
        ).aggregate(total=Sum('prix_total'))['total'] or 0
        
        # Moyennes
        if stats['total_reservations'] > 0:
            stats['duree_moyenne'] = reservations.aggregate(
                moyenne=Avg('nombre_nuits')
            )['moyenne'] or 0
            
            stats['personnes_moyenne'] = reservations.aggregate(
                moyenne=Avg('nombre_personnes')
            )['moyenne'] or 0
            
            stats['prix_moyen'] = reservations.aggregate(
                moyenne=Avg('prix_total')
            )['moyenne'] or 0
        else:
            stats.update({
                'duree_moyenne': 0,
                'personnes_moyenne': 0,
                'prix_moyen': 0
            })
        
        # Prochaines échéances
        stats['arrivees_aujourd_hui'] = reservations.filter(
            statut='confirmee',
            date_debut=timezone.now().date()
        ).count()
        
        stats['departs_aujourd_hui'] = reservations.filter(
            statut='confirmee',
            date_fin=timezone.now().date()
        ).count()
        
        return stats
    
    @staticmethod
    def get_evolution_reservations(user, nb_mois: int = 12) -> List[Dict]:
        """Récupère l'évolution des réservations sur plusieurs mois"""
        reservations = ReservationService.get_reservations_for_user(user)
        
        evolution = []
        for i in range(nb_mois):
            date_ref = timezone.now().replace(day=1) - timedelta(days=30 * i)
            debut_mois = date_ref.replace(day=1)
            fin_mois = (debut_mois + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            stats_mois = reservations.filter(
                date_creation__gte=debut_mois,
                date_creation__lte=fin_mois
            ).aggregate(
                nombre=Count('id'),
                revenus=Sum('prix_total', filter=Q(statut__in=['confirmee', 'terminee']))
            )
            
            evolution.append({
                'mois': debut_mois.strftime('%Y-%m'),
                'nom_mois': debut_mois.strftime('%B %Y'),
                'nombre_reservations': stats_mois['nombre'] or 0,
                'revenus': stats_mois['revenus'] or 0
            })
        
        evolution.reverse()
        return evolution
    
    @staticmethod
    def get_top_maisons(user, limite: int = 10) -> List[Dict]:
        """Récupère les maisons les plus réservées"""
        reservations = ReservationService.get_reservations_for_user(user)
        
        return reservations.values(
            'maison__id', 'maison__nom', 'maison__ville__nom'
        ).annotate(
            nombre_reservations=Count('id'),
            revenus_total=Sum('prix_total', filter=Q(statut__in=['confirmee', 'terminee'])),
            note_moyenne=Avg('evaluation__note_globale')
        ).order_by('-nombre_reservations')[:limite]