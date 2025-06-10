# users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from PIL import Image

class User(AbstractUser):
    """Modèle utilisateur personnalisé pour RepAvi"""
    
    TYPE_CHOICES = [
        ('locataire', 'Locataire'),
        ('proprietaire', 'Propriétaire'),
        ('admin', 'Administrateur'),
    ]
    
    # Informations personnelles étendues
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
        null=True,
        default='users/default-avatar.png'
    )
    
    # Adresse
    adresse = models.CharField(max_length=255, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    code_postal = models.CharField(max_length=10, blank=True)
    pays = models.CharField(max_length=100, default='France')
    
    # Type d'utilisateur et statut
    type_utilisateur = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='locataire'
    )
    
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
    
    # Utiliser le username comme nom d'utilisateur (pas l'email)
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']
    
    def save(self, *args, **kwargs):
        # Redimensionner la photo de profil
        super().save(*args, **kwargs)
        
        if self.photo_profil and hasattr(self.photo_profil, 'path'):
            try:
                img = Image.open(self.photo_profil.path)
                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size)
                    img.save(self.photo_profil.path)
            except Exception:
                pass  # Ignore les erreurs d'image
    
    @property
    def nom_complet(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def est_proprietaire(self):
        return self.type_utilisateur == 'proprietaire'
    
    @property
    def est_locataire(self):
        return self.type_utilisateur == 'locataire'
    
    @property
    def est_admin(self):
        return self.type_utilisateur == 'admin' or self.is_superuser
    
    def __str__(self):
        return f"{self.nom_complet} ({self.email})"
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'


class ProfilProprietaire(models.Model):
    """Profil étendu pour les propriétaires"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil_proprietaire')
    
    # Informations légales
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
    
    # Préférences
    auto_acceptation = models.BooleanField(default=False, help_text="Acceptation automatique des réservations")
    delai_reponse_max = models.PositiveIntegerField(default=24, help_text="Délai de réponse en heures")
    
    def __str__(self):
        return f"Propriétaire: {self.user.nom_complet}"
    
    class Meta:
        verbose_name = 'Profil Propriétaire'
        verbose_name_plural = 'Profils Propriétaires'


class ProfilLocataire(models.Model):
    """Profil étendu pour les locataires"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil_locataire')
    
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
    
    # Préférences de communication
    langue_preferee = models.CharField(max_length=10, default='fr')
    
    def __str__(self):
        return f"Locataire: {self.user.nom_complet}"
    
    class Meta:
        verbose_name = 'Profil Locataire'
        verbose_name_plural = 'Profils Locataires'


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