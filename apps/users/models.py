# apps/users/models.py - Profils utilisateurs selon cahier
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Utilisateur RepAvi Lodges
    Super Admin, Gestionnaire et Réceptionniste - PAS de profil Client
    """
    PROFIL_CHOICES = [
        ('super_admin', 'Super Administrateur'),
        ('gestionnaire', 'Gestionnaire'),
        ('receptionniste', 'Réceptionniste'),
    ]

    profil = models.CharField(
        max_length=20,
        choices=PROFIL_CHOICES,
        default='gestionnaire'
    )
    telephone = models.CharField(max_length=20, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)
    derniere_activite = models.DateTimeField(auto_now=True)

    def is_super_admin(self):
        return self.profil == 'super_admin'

    def is_gestionnaire(self):
        return self.profil in ['super_admin', 'gestionnaire']

    def is_receptionniste(self):
        return self.profil in ['super_admin', 'gestionnaire', 'receptionniste']
    
    def save(self, *args, **kwargs):
        """
        Surcharge save pour attribuer automatiquement le profil super_admin
        aux superusers Django créés via createsuperuser
        """
        # Si c'est un superuser Django et qu'il n'a pas encore de profil spécifique
        if self.is_superuser and self.profil == 'gestionnaire':
            self.profil = 'super_admin'
        
        # Si on force le profil super_admin, s'assurer que c'est aussi un superuser Django
        if self.profil == 'super_admin':
            self.is_superuser = True
            self.is_staff = True
            
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    
class ActionLog(models.Model):
    """Log automatique des actions système selon cahier"""
    
    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Modification'), 
        ('delete', 'Suppression'),
        ('login', 'Connexion'),
        ('logout', 'Déconnexion'),
        ('view', 'Consultation'),
    ]
    
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)  # Ex: 'Reservation', 'Client'
    object_id = models.CharField(max_length=50, null=True, blank=True)
    object_repr = models.CharField(max_length=200)  # Représentation de l'objet
    
    # Détails
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    url = models.URLField(blank=True)
    method = models.CharField(max_length=10, blank=True)  # GET, POST, PUT, DELETE
    
    # Métadonnées
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, default='{}')  # JSON sous forme de texte
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Journal des actions'
        verbose_name_plural = 'Journal des actions'
    
    def __str__(self):
        user_str = self.utilisateur.username if self.utilisateur else 'Anonyme'
        return f"{user_str} - {self.get_action_display()} {self.model_name} - {self.timestamp}"


