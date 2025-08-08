# ==========================================
# apps/appartements/models.py - Gestion appartements
# ==========================================
from django.db import models
from django.utils.text import slugify

class Appartement(models.Model):
    """
    Appartement RepAvi selon specs exactes du cahier
    """
    TYPE_CHOICES = [
        ('studio', 'Studio'),
        ('t1', 'T1'),
        ('t2', 'T2'),
    ]
    
    STATUT_CHOICES = [
        ('disponible', 'Disponible'),
        ('occupe', 'Occupé'),
        ('maintenance', 'Maintenance'),
    ]
    
    # Identification (selon cahier)
    numero = models.CharField(max_length=10, unique=True, verbose_name='Numéro')
    type_logement = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name='Type')
    maison = models.CharField(max_length=100, verbose_name='Maison')
    
    # Tarification (prix unique et simple)
    prix_par_nuit = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name='Prix par nuit (FCFA)'
    )
    
    # État
    statut = models.CharField(
        max_length=20, 
        choices=STATUT_CHOICES,
        default='disponible',
        verbose_name='Statut'
    )
    
    # Équipements (liste simple selon cahier)
    equipements = models.JSONField(
        default=list,
        help_text='Liste simple : TV, Frigo, Climatisation, etc.',
        verbose_name='Équipements'
    )
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.numero} - {self.get_type_logement_display()} ({self.maison})"
    
    def get_occupation_actuelle(self):
        """Vérifier si appartement occupé aujourd'hui"""
        from django.utils import timezone
        from apps.reservations.models import Reservation
        
        today = timezone.now().date()
        return Reservation.objects.filter(
            appartement=self,
            date_arrivee__lte=today,
            date_depart__gt=today,
            statut__in=['confirmee', 'en_cours']
        ).exists()
    
    def get_photo_principale(self):
        return self.photos.filter(est_principale=True).first()

    class Meta:
        verbose_name = 'Appartement'
        verbose_name_plural = 'Appartements'
        ordering = ['numero']


class PhotoAppartement(models.Model):
    """Photos par pièce selon cahier"""
    appartement = models.ForeignKey(Appartement, on_delete=models.CASCADE, related_name='photos')
    nom_piece = models.CharField(max_length=50, verbose_name='Pièce')
    photo = models.ImageField(upload_to='appartements/photos/')
    est_principale = models.BooleanField(default=False, verbose_name='Photo principale')
    ordre = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Photo Appartement'
        verbose_name_plural = 'Photos Appartements'
        ordering = ['ordre', 'nom_piece']


