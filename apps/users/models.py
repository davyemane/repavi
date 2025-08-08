# apps/users/models.py - Profils utilisateurs selon cahier
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Utilisateur RepAvi Lodges
    Seulement Super Admin et Gestionnaire - PAS de profil Client
    """
    PROFIL_CHOICES = [
        ('super_admin', 'Super Administrateur'),
        ('gestionnaire', 'Gestionnaire'),
    ]
    
    profil = models.CharField(
        max_length=20, 
        choices=PROFIL_CHOICES,
        default='gestionnaire'
    )
    telephone = models.CharField(max_length=20, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def is_super_admin(self):
        return self.profil == 'super_admin'
    
    def is_gestionnaire(self):
        return self.profil in ['super_admin', 'gestionnaire']
    
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