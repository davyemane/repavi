# users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from PIL import Image

class User(AbstractUser):
    """Modèle utilisateur personnalisé pour RepAvi - Refactorisé selon cahier technique"""
    
    # NOUVEAUX RÔLES selon le cahier technique
    ROLE_CHOICES = [
        ('CLIENT', 'Client'),
        ('GESTIONNAIRE', 'Gestionnaire'), 
        ('SUPER_ADMIN', 'Super Admin'),
    ]
    
    # MIGRATION : type_utilisateur → role
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='CLIENT',
        verbose_name="Rôle"
    )
    
    # Informations personnelles étendues (gardées de l'ancien modèle)
    email = models.EmailField(unique=True)
    telephone = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Format: '+999999999'. 9 à 15 chiffres autorisés."
        )],
        blank=True
    )
    date_naissance = models.DateField(null=True, blank=True)
    photo_profil = models.ImageField(
        upload_to='users/photos/',
        blank=True,
        null=True
    )
    
    # Adresse
    adresse = models.CharField(max_length=255, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    code_postal = models.CharField(max_length=10, blank=True)
    pays = models.CharField(max_length=100, default='France')
    
    # Vérifications
    email_verifie = models.BooleanField(default=False)
    telephone_verifie = models.BooleanField(default=False)
    identite_verifiee = models.BooleanField(default=False)
    
    # Préférences
    newsletter = models.BooleanField(default=True)
    notifications_email = models.BooleanField(default=True)
    notifications_sms = models.BooleanField(default=False)
    
    # Métadonnées
    date_derniere_connexion_complete = models.DateTimeField(null=True, blank=True)
    ip_derniere_connexion = models.GenericIPAddressField(null=True, blank=True)
    
    # Configuration Django
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Redimensionner la photo de profil
        if self.photo_profil and hasattr(self.photo_profil, 'path'):
            try:
                img = Image.open(self.photo_profil.path)
                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size)
                    img.save(self.photo_profil.path)
            except Exception:
                pass
    
    # NOUVELLES MÉTHODES selon le cahier technique
    def is_client(self):
        """Vérifie si l'utilisateur est un client"""
        return self.role == 'CLIENT'
    
    def is_gestionnaire(self):
        """Vérifie si l'utilisateur est un gestionnaire"""
        return self.role == 'GESTIONNAIRE'
    
    def is_super_admin(self):
        """Vérifie si l'utilisateur est un super admin"""
        return self.role == 'SUPER_ADMIN'
    
    def has_gestionnaire_permissions(self):
        """Vérifie si l'utilisateur a les permissions de gestionnaire ou plus"""
        return self.role in ['GESTIONNAIRE', 'SUPER_ADMIN'] or self.is_superuser
    
    def can_manage_maisons(self):
        """Peut gérer les maisons"""
        return self.has_gestionnaire_permissions()
    
    def can_manage_clients(self):
        """Peut gérer les clients"""
        return self.has_gestionnaire_permissions()
    
    def can_view_statistics(self):
        """Peut voir les statistiques"""
        return self.has_gestionnaire_permissions()
    
    def can_generate_pdf(self):
        """Peut générer des PDFs"""
        return self.has_gestionnaire_permissions()
    
    # COMPATIBILITÉ avec l'ancien code
    @property
    def type_utilisateur(self):
        """Compatibilité : Mapping vers les anciens types"""
        mapping = {
            'CLIENT': 'locataire',
            'GESTIONNAIRE': 'proprietaire', 
            'SUPER_ADMIN': 'admin'
        }
        return mapping.get(self.role, 'locataire')
    
    @property
    def est_proprietaire(self):
        """Compatibilité : ancien proprietaire = nouveau gestionnaire"""
        return self.is_gestionnaire()
    
    @property
    def est_locataire(self):
        """Compatibilité : ancien locataire = nouveau client"""
        return self.is_client()
    
    @property
    def est_admin(self):
        """Compatibilité : admin"""
        return self.is_super_admin() or self.is_superuser
    
    @property
    def nom_complet(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def __str__(self):
        return f"{self.nom_complet} ({self.email})"
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        permissions = [
            ('can_view_maisons', 'Peut consulter les maisons'),
            ('can_make_reservation', 'Peut faire des réservations'),
            ('can_give_review', 'Peut donner des avis'),
            ('can_manage_clients', 'Peut gérer les clients'),
            ('can_manage_maisons', 'Peut gérer les maisons'),
            ('can_manage_reservations', 'Peut gérer les réservations'),
            ('can_generate_pdf', 'Peut générer des PDFs'),
            ('can_view_statistics', 'Peut voir les statistiques'),
            ('can_manage_system', 'Peut gérer le système'),
        ]


# Profils étendus selon les nouveaux rôles
class ProfilClient(models.Model):
    """Profil étendu pour les clients (anciens locataires)"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil_client')
    
    # Préférences de voyage
    type_sejour_prefere = models.CharField(
        max_length=50,
        choices=[
            ('business', 'Professionnel'),
            ('leisure', 'Loisirs'),
            ('family', 'Famille'),
            ('couple', 'Couple'),
            ('friends', 'Entre amis'),
        ],
        blank=True
    )
    
    # Historique
    nombre_sejours = models.PositiveIntegerField(default=0)
    note_moyenne = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    nombre_evaluations = models.PositiveIntegerField(default=0)
    
    # Documents
    piece_identite = models.FileField(upload_to='users/documents/', blank=True)
    
    # Préférences
    langue_preferee = models.CharField(max_length=10, default='fr')
    
    def __str__(self):
        return f"Client: {self.user.nom_complet}"
    
    class Meta:
        verbose_name = 'Profil Client'
        verbose_name_plural = 'Profils Clients'


class ProfilGestionnaire(models.Model):
    """Profil étendu pour les gestionnaires (anciens propriétaires)"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil_gestionnaire')
    
    # Informations professionnelles
    siret = models.CharField(max_length=14, blank=True, help_text="Numéro SIRET si professionnel")
    raison_sociale = models.CharField(max_length=200, blank=True)
    
    # Informations bancaires
    iban = models.CharField(max_length=34, blank=True)
    bic = models.CharField(max_length=11, blank=True)
    
    # Documents de vérification
    piece_identite = models.FileField(upload_to='users/documents/', blank=True)
    justificatif_domicile = models.FileField(upload_to='users/documents/', blank=True)
    kbis = models.FileField(upload_to='users/documents/', blank=True, help_text="Pour les professionnels")
    
    # Statut et notes
    note_moyenne = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    nombre_evaluations = models.PositiveIntegerField(default=0)
    verifie = models.BooleanField(default=False)
    
    # Préférences de gestion
    auto_acceptation = models.BooleanField(default=False, help_text="Acceptation automatique des réservations")
    delai_reponse_max = models.PositiveIntegerField(default=24, help_text="Délai de réponse en heures")
    
    def __str__(self):
        return f"Gestionnaire: {self.user.nom_complet}"
    
    class Meta:
        verbose_name = 'Profil Gestionnaire'
        verbose_name_plural = 'Profils Gestionnaires'


# Tokens de vérification (gardés identiques)
class TokenVerificationEmail(models.Model):
    """Token pour vérification d'email"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    class Meta:
        verbose_name = 'Token de vérification email'
        verbose_name_plural = 'Tokens de vérification email'


class PasswordResetToken(models.Model):
    """Token pour réinitialisation de mot de passe"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    class Meta:
        verbose_name = 'Token de réinitialisation'
        verbose_name_plural = 'Tokens de réinitialisation'