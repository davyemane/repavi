# ==========================================
# apps/reservations/models.py - AVEC REDUCTION
# ==========================================
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal

class Reservation(models.Model):
    STATUT_CHOICES = [
        ('confirmee', 'Confirmée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    
    # Liens
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE)
    appartement = models.ForeignKey('appartements.Appartement', on_delete=models.CASCADE)
    
    # Dates
    date_arrivee = models.DateField(verbose_name='Date d\'arrivée')
    date_depart = models.DateField(verbose_name='Date de départ')
    
    # Calculs automatiques
    nombre_nuits = models.PositiveIntegerField(verbose_name='Nombre de nuits', default=1)
    
    # NOUVEAU: Réduction
    reduction = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name='Réduction (FCFA)',
        default=0,
        help_text='Montant de la réduction appliquée sur le prix total'
    )
    
    prix_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name='Prix total (FCFA)',
        default=0
    )
    
    # Statut
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='confirmee')
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    gestionnaire = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    def clean(self):
        if self.date_depart and self.date_arrivee:
            if self.date_depart <= self.date_arrivee:
                raise ValidationError('La date de départ doit être après l\'arrivée')
        
        # Vérifier que la réduction ne dépasse pas le prix de base
        if self.reduction and self.appartement_id and self.nombre_nuits:
            from apps.appartements.models import Appartement
            appartement = Appartement.objects.get(pk=self.appartement_id)
            prix_base = Decimal(str(self.nombre_nuits)) * appartement.prix_par_nuit
            if self.reduction > prix_base:
                raise ValidationError(f'La réduction ({self.reduction} FCFA) ne peut pas dépasser le prix de base ({prix_base} FCFA)')
        
        # Vérifier conflits
        if self.appartement and self.date_arrivee and self.date_depart:
            conflits = Reservation.objects.filter(
                appartement=self.appartement,
                statut__in=['confirmee', 'en_cours']
            ).exclude(pk=self.pk if self.pk else None)
            
            for conf in conflits:
                if (self.date_arrivee < conf.date_depart and 
                    self.date_depart > conf.date_arrivee):
                    raise ValidationError(f'Conflit avec réservation {conf.pk}')
    
    def save(self, *args, **kwargs):
        # Calcul automatique AVEC réduction
        if self.date_arrivee and self.date_depart:
            self.nombre_nuits = (self.date_depart - self.date_arrivee).days
            if self.appartement_id:
                try:
                    from apps.appartements.models import Appartement
                    appartement = Appartement.objects.get(pk=self.appartement_id)
                    prix_base = Decimal(str(self.nombre_nuits)) * appartement.prix_par_nuit
                    # Appliquer la réduction
                    self.prix_total = prix_base - (self.reduction or Decimal('0'))
                except Exception:
                    self.prix_total = Decimal('0')
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.client} - {self.appartement.numero} ({self.date_arrivee})"
    
    class Meta:
        verbose_name = 'Réservation'
        verbose_name_plural = 'Réservations'
        ordering = ['-date_arrivee']