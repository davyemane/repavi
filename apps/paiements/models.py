# ==========================================
# apps/paiements/models.py - Paiements par tranches CORRIGÉ
# ==========================================
from django.db import models
from decimal import Decimal

class EcheancierPaiement(models.Model):
    """
    Paiement par tranches simplifié selon cahier
    """
    MODE_PAIEMENT_CHOICES = [
        ('especes', 'Espèces'),
        ('virement', 'Virement bancaire'),
        ('mobile_money_orange', 'Mobile Money Orange'),
        ('mobile_money_mtn', 'Mobile Money MTN'),
        ('cheque', 'Chèque'),
    ]
    
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('paye', 'Payé'),
    ]
    
    TYPE_CHOICES = [
        ('acompte', 'Acompte'),
        ('solde', 'Solde'),
    ]
    
    # Liens
    reservation = models.ForeignKey(
        'reservations.Reservation', 
        on_delete=models.CASCADE,
        related_name='echeanciers'  # AJOUT du related_name
    )
    
    # Informations écheance
    type_paiement = models.CharField(max_length=20, choices=TYPE_CHOICES)
    montant_prevu = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Montant prévu')
    date_echeance = models.DateField(verbose_name='Date échéance')
    
    # Paiement effectué
    montant_paye = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Montant payé')
    mode_paiement = models.CharField(max_length=30, choices=MODE_PAIEMENT_CHOICES, blank=True)
    date_paiement = models.DateField(null=True, blank=True, verbose_name='Date paiement')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    
    # Notes
    commentaire = models.TextField(blank=True, verbose_name='Commentaire')
    
    def __str__(self):
        return f"{self.reservation} - {self.get_type_paiement_display()} : {self.montant_prevu} FCFA"
    
    @property
    def solde_restant(self):
        """Solde restant pour cette échéance spécifique"""
        return self.montant_prevu - self.montant_paye
    
    def save(self, *args, **kwargs):
        """NE PAS recalculer automatiquement pour éviter les bugs"""
        super().save(*args, **kwargs)
        # Commenté pour éviter le bug du solde incorrect
        # self.recalculer_echeancier_reservation()
    
    def recalculer_echeancier_reservation(self):
        """Recalculer l'échéancier complet de la réservation après paiement"""
        total_paye = EcheancierPaiement.objects.filter(
            reservation=self.reservation
        ).aggregate(total=models.Sum('montant_paye'))['total'] or Decimal('0')
        
        total_reservation = self.reservation.prix_total
        solde_global = total_reservation - total_paye
        
        # Mettre à jour l'échéance solde
        echeance_solde = EcheancierPaiement.objects.filter(
            reservation=self.reservation,
            type_paiement='solde'
        ).first()
        
        if echeance_solde and solde_global >= 0:
            # Recalculer le montant prévu du solde
            echeance_solde.montant_prevu = solde_global
            if solde_global == 0:
                echeance_solde.statut = 'paye'
                echeance_solde.montant_paye = echeance_solde.montant_prevu
            else:
                echeance_solde.statut = 'en_attente'
            # Éviter la récursion
            super(EcheancierPaiement, echeance_solde).save()
    
    @classmethod
    def get_situation_reservation(cls, reservation):
        """Obtenir la situation financière d'une réservation"""
        echeances = cls.objects.filter(reservation=reservation)
        
        total_prevu = echeances.aggregate(
            total=models.Sum('montant_prevu')
        )['total'] or Decimal('0')
        
        total_paye = echeances.aggregate(
            total=models.Sum('montant_paye')
        )['total'] or Decimal('0')
        
        return {
            'total_prevu': total_prevu,
            'total_paye': total_paye,
            'solde_restant': reservation.prix_total - total_paye,
            'taux_paiement': (total_paye / reservation.prix_total * 100) if reservation.prix_total > 0 else 0
        }
    
    class Meta:
        verbose_name = 'Échéancier Paiement'
        verbose_name_plural = 'Échéanciers Paiements'
        ordering = ['date_echeance']
        # Éviter les doublons par type pour une même réservation
        unique_together = ['reservation', 'type_paiement']