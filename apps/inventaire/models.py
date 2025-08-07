# ==========================================
# apps/inventaire/models.py - Inventaire équipements SIMPLIFIÉ
# ==========================================
from django.db import models

class EquipementAppartement(models.Model):
    """
    Inventaire équipements par appartement selon cahier
    """
    ETAT_CHOICES = [
        ('bon', 'Bon'),
        ('usage', 'Usage'),
        ('defectueux', 'Défectueux'),
        ('hors_service', 'Hors service'),
    ]
    
    # Liens
    appartement = models.ForeignKey('appartements.Appartement', on_delete=models.CASCADE)
    
    # Informations équipement (selon cahier)
    nom = models.CharField(max_length=100, verbose_name='Nom équipement')
    etat = models.CharField(max_length=20, choices=ETAT_CHOICES, default='bon')
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Prix d\'achat (FCFA)')
    date_achat = models.DateField(verbose_name='Date d\'achat')
    
    # Informations basiques (selon cahier)
    photo = models.ImageField(upload_to='inventaire/', blank=True)
    commentaire = models.TextField(blank=True, verbose_name='Notes')
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.appartement.numero} - {self.nom}"
    
    class Meta:
        verbose_name = 'Équipement'
        verbose_name_plural = 'Équipements'
        ordering = ['appartement__numero', 'nom']