# ==========================================
# apps/comptabilite/models.py - Comptabilité simple
# ==========================================
from django.db import models
from django.db.models import Sum

class ComptabiliteAppartement(models.Model):
    """
    Comptabilité simple par appartement selon cahier
    PAS de calculs complexes - juste addition/soustraction
    """
    TYPE_MOUVEMENT_CHOICES = [
        ('revenu', 'Revenu'),
        ('charge', 'Charge'),
    ]
    
    # Liens
    appartement = models.ForeignKey('appartements.Appartement', on_delete=models.CASCADE)
    reservation = models.ForeignKey('reservations.Reservation', on_delete=models.CASCADE, null=True, blank=True)
    
    # Mouvement financier
    type_mouvement = models.CharField(max_length=10, choices=TYPE_MOUVEMENT_CHOICES)
    libelle = models.CharField(max_length=200, verbose_name='Libellé')
    montant = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Montant (FCFA)')
    date_mouvement = models.DateField(verbose_name='Date')
    
    # Métadonnées
    date_saisie = models.DateTimeField(auto_now_add=True)
    gestionnaire = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        signe = '+' if self.type_mouvement == 'revenu' else '-'
        return f"{self.appartement.numero} - {signe}{self.montant} FCFA ({self.libelle})"
    
    @classmethod
    def get_revenus_mois(cls, appartement, annee, mois):
        """Revenus du mois pour un appartement"""
        return cls.objects.filter(
            appartement=appartement,
            type_mouvement='revenu',
            date_mouvement__year=annee,
            date_mouvement__month=mois
        ).aggregate(total=Sum('montant'))['total'] or 0
    
    @classmethod  
    def get_charges_mois(cls, appartement, annee, mois):
        """Charges du mois pour un appartement"""
        return cls.objects.filter(
            appartement=appartement,
            type_mouvement='charge',
            date_mouvement__year=annee,
            date_mouvement__month=mois
        ).aggregate(total=Sum('montant'))['total'] or 0
    
    class Meta:
        verbose_name = 'Mouvement Comptable'
        verbose_name_plural = 'Mouvements Comptables'
        ordering = ['-date_mouvement']
