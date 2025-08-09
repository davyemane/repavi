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
    appartement = models.ForeignKey(
        'appartements.Appartement', 
        on_delete=models.CASCADE,
        related_name='inventaire_equipements',  # Fix pour éviter conflit avec champ existant
        verbose_name='Appartement'
    )
    
    # Informations équipement (selon cahier)
    nom = models.CharField(max_length=100, verbose_name='Nom équipement')
    etat = models.CharField(max_length=20, choices=ETAT_CHOICES, default='bon', verbose_name='État')
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Prix d\'achat (FCFA)')
    date_achat = models.DateField(verbose_name='Date d\'achat')
    
    # Informations basiques (selon cahier)
    photo = models.ImageField(upload_to='inventaire/', blank=True, verbose_name='Photo')
    commentaire = models.TextField(blank=True, verbose_name='Notes et commentaires')
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.appartement.numero} - {self.nom}"
    
    def get_etat_couleur(self):
        """Retourne la couleur CSS pour l'état selon cahier"""
        couleurs = {
            'bon': 'green',
            'usage': 'blue', 
            'defectueux': 'orange',
            'hors_service': 'red'
        }
        return couleurs.get(self.etat, 'gray')
    
    def est_fonctionnel(self):
        """Vérifie si l'équipement est fonctionnel selon cahier"""
        return self.etat in ['bon', 'usage']
    
    def necessite_attention(self):
        """Vérifie si l'équipement nécessite une attention selon cahier"""
        return self.etat in ['defectueux', 'hors_service']
    
    class Meta:
        verbose_name = 'Équipement'
        verbose_name_plural = 'Équipements'
        ordering = ['appartement__numero', 'nom']
        indexes = [
            models.Index(fields=['appartement', 'etat']),
            models.Index(fields=['etat']),
            models.Index(fields=['date_creation']),
        ]