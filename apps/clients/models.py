# ==========================================
# apps/clients/models.py - Fiche client simple
# ==========================================
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

class Client(models.Model):
    """
    Fiche client simple selon cahier des charges
    """
    # Identité (selon cahier)
    nom = models.CharField(max_length=100, verbose_name='Nom')
    prenom = models.CharField(max_length=100, verbose_name='Prénom')

    # Téléphone avec code pays international
    telephone = PhoneNumberField(
        verbose_name='Téléphone',
        region='CM',  # Région par défaut: Cameroun
        unique=True,
        error_messages={
            'unique': 'Ce numéro de téléphone est déjà utilisé par un autre client.'
        },
        help_text='Format international (ex: +237 6XX XXX XXX)'
    )

    email = models.EmailField(
        verbose_name='Email',
        unique=True,
        error_messages={
            'unique': 'Cette adresse email est déjà utilisée par un autre client.'
        }
    )

    # Numéro d'identité (CNI, Passeport, etc.)
    numero_identite = models.CharField(
        max_length=50,
        verbose_name='Numéro d\'identité',
        help_text='Numéro de CNI, passeport ou autre pièce d\'identité',
        unique=True,
        error_messages={
            'unique': 'Ce numéro d\'identité est déjà utilisé par un autre client.'
        }
    )
    
    # Document (selon cahier)
    piece_identite = models.ImageField(
        upload_to='clients/documents/',
        verbose_name='Pièce d\'identité (photo)'
    )
    
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