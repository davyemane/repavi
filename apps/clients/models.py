# ==========================================
# apps/clients/models.py - Fiche client simple
# ==========================================
from django.db import models

class Client(models.Model):
    """
    Fiche client simple selon cahier des charges
    """
    # Identité (selon cahier)
    nom = models.CharField(max_length=100, verbose_name='Nom')
    prenom = models.CharField(max_length=100, verbose_name='Prénom')
    telephone = models.CharField(max_length=20, verbose_name='Téléphone')
    email = models.EmailField(verbose_name='Email')
    
    # Document (selon cahier)
    piece_identite = models.ImageField(
        upload_to='clients/documents/',
        verbose_name='Pièce d\'identité (photo)'
    )

    # numero cni ou passeport
    numero_identite = models.CharField(max_length=100, verbose_name='Numéro de CNI ou Passeport')

    # Adresse (selon cahier)
    adresse_residence = models.TextField(verbose_name='Résidence habituelle')
    
    # Contact d'urgence (selon cahier)
    contact_urgence_nom = models.CharField(max_length=100, verbose_name='Contact urgence - Nom')
    contact_urgence_tel = models.CharField(max_length=20, verbose_name='Contact urgence - Téléphone')
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.prenom} {self.nom}"
    
    def get_nombre_sejours(self):
        """Nombre de séjours effectués"""
        return self.reservation_set.filter(statut='terminee').count()
    
    class Meta:
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        ordering = ['nom', 'prenom']
