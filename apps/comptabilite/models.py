# ==========================================
# apps/comptabilite/models.py - Comptabilité simple CORRIGÉ
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
        """Revenus du mois pour un appartement - CORRIGÉ"""
        result = cls.objects.filter(
            appartement=appartement,
            type_mouvement='revenu',
            date_mouvement__year=annee,
            date_mouvement__month=mois
        ).aggregate(total=Sum('montant'))
        
        return result.get('total') or 0
    
    @classmethod  
    def get_charges_mois(cls, appartement, annee, mois):
        """Charges du mois pour un appartement - CORRIGÉ"""
        result = cls.objects.filter(
            appartement=appartement,
            type_mouvement='charge',
            date_mouvement__year=annee,
            date_mouvement__month=mois
        ).aggregate(total=Sum('montant'))
        
        return result.get('total') or 0
    
    @classmethod
    def get_benefice_mois(cls, appartement, annee, mois):
        """Bénéfice du mois pour un appartement"""
        revenus = cls.get_revenus_mois(appartement, annee, mois)
        charges = cls.get_charges_mois(appartement, annee, mois)
        return revenus - charges
    
    @classmethod
    def get_statistiques_appartement(cls, appartement, annee=None):
        """Statistiques annuelles d'un appartement - CORRIGÉ"""
        from django.utils import timezone
        
        if not annee:
            annee = timezone.now().year
        
        mouvements = cls.objects.filter(
            appartement=appartement,
            date_mouvement__year=annee
        )
        
        # CORRECTIONS : Utiliser .get() au lieu d'accès direct
        revenus_result = mouvements.filter(type_mouvement='revenu').aggregate(total=Sum('montant'))
        charges_result = mouvements.filter(type_mouvement='charge').aggregate(total=Sum('montant'))
        
        revenus_total = revenus_result.get('total') or 0
        charges_total = charges_result.get('total') or 0
        
        return {
            'appartement': appartement,
            'annee': annee,
            'revenus_total': revenus_total,
            'charges_total': charges_total,
            'benefice': revenus_total - charges_total,
            'taux_rentabilite': (revenus_total / charges_total * 100) if charges_total > 0 else 0,
            'nombre_mouvements': mouvements.count()
        }
    
    @classmethod
    def get_tableau_bord_global(cls, gestionnaire=None, annee=None):
        """Tableau de bord global pour tous les appartements - CORRIGÉ"""
        from django.utils import timezone
        from apps.appartements.models import Appartement
        
        if not annee:
            annee = timezone.now().year
        
        # Filtrer les appartements selon le gestionnaire
        if gestionnaire and hasattr(gestionnaire, 'is_gestionnaire') and gestionnaire.is_gestionnaire():
            appartements = Appartement.objects.filter(gestionnaire=gestionnaire)
        else:
            appartements = Appartement.objects.all()
        
        mouvements = cls.objects.filter(
            appartement__in=appartements,
            date_mouvement__year=annee
        )
        
        # CORRECTIONS : Utiliser .get() au lieu d'accès direct
        revenus_result = mouvements.filter(type_mouvement='revenu').aggregate(total=Sum('montant'))
        charges_result = mouvements.filter(type_mouvement='charge').aggregate(total=Sum('montant'))
        
        revenus_total = revenus_result.get('total') or 0
        charges_total = charges_result.get('total') or 0
        
        # Statistiques par appartement
        stats_appartements = []
        for appartement in appartements:
            stats = cls.get_statistiques_appartement(appartement, annee)
            stats_appartements.append(stats)
        
        return {
            'annee': annee,
            'nb_appartements': appartements.count(),
            'revenus_total': revenus_total,
            'charges_total': charges_total,
            'benefice_total': revenus_total - charges_total,
            'appartements': stats_appartements,
            'taux_rentabilite_global': (revenus_total / charges_total * 100) if charges_total > 0 else 0
        }
    
    class Meta:
        verbose_name = 'Mouvement Comptable'
        verbose_name_plural = 'Mouvements Comptables'
        ordering = ['-date_mouvement']
        indexes = [
            models.Index(fields=['appartement', 'date_mouvement']),
            models.Index(fields=['type_mouvement', 'date_mouvement']),
        ]