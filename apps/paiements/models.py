# ==========================================
# apps/paiements/models.py - Paiements par tranches SIMPLIFIÉ
# ==========================================
from django.db import models

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
    reservation = models.ForeignKey('reservations.Reservation', on_delete=models.CASCADE)
    
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
        return self.montant_prevu - self.montant_paye
    
    class Meta:
        verbose_name = 'Échéancier Paiement'
        verbose_name_plural = 'Échéanciers Paiements'
        ordering = ['date_echeance']

