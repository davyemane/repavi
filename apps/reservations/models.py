# ==========================================
# apps/reservations/models.py - CORRIGÉ
# ==========================================
from django.db import models
from django.core.exceptions import ValidationError
from datetime import timedelta

class Reservation(models.Model):
    """
    Réservation selon cahier des charges
    """
    STATUT_CHOICES = [
        ('confirmee', 'Confirmée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    
    # Liens (selon cahier)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE)
    appartement = models.ForeignKey('appartements.Appartement', on_delete=models.CASCADE)
    
    # Dates (selon cahier)
    date_arrivee = models.DateField(verbose_name='Date d\'arrivée')
    date_depart = models.DateField(verbose_name='Date de départ')
    
    # Calculs automatiques - VALEURS PAR DÉFAUT AJOUTÉES
    nombre_nuits = models.PositiveIntegerField(
        verbose_name='Nombre de nuits',
        default=1
    )
    prix_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name='Prix total (FCFA)',
        default=0
    )
    
    # Statut
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='confirmee',
        verbose_name='Statut'
    )
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    gestionnaire = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    def clean(self):
        """Validation des dates et conflits"""
        if self.date_depart and self.date_arrivee:
            if self.date_depart <= self.date_arrivee:
                raise ValidationError('La date de départ doit être après l\'arrivée')
        
        # Vérifier conflits selon cahier
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
        # Calcul automatique selon cahier AVANT validation
        if self.date_arrivee and self.date_depart:
            self.nombre_nuits = (self.date_depart - self.date_arrivee).days
            if self.appartement_id:  # Vérifier que l'appartement existe
                try:
                    if hasattr(self.appartement, 'prix_par_nuit'):
                        self.prix_total = self.nombre_nuits * self.appartement.prix_par_nuit
                    else:
                        # Si l'appartement n'est pas encore chargé
                        from apps.appartements.models import Appartement
                        appartement = Appartement.objects.get(pk=self.appartement_id)
                        self.prix_total = self.nombre_nuits * appartement.prix_par_nuit
                except:
                    # En cas d'erreur, on garde les valeurs par défaut
                    pass
        
        # Validation avant sauvegarde
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.client} - {self.appartement.numero} ({self.date_arrivee})"
    
    class Meta:
        verbose_name = 'Réservation'
        verbose_name_plural = 'Réservations'
        ordering = ['-date_arrivee']