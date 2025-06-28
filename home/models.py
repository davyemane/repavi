from django.db import models
from django.conf import settings
from django.urls import reverse
from PIL import Image
from django.db.models import Q, Count

class Ville(models.Model):
    nom = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    departement = models.CharField(max_length=100)
    pays = models.CharField(max_length=100, default='France')
    
    def __str__(self):
        return f"{self.nom}, {self.departement}"
    
    class Meta:
        verbose_name = 'Ville'
        verbose_name_plural = 'Villes'

class CategorieMaison(models.Model):
    nom = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    couleur = models.CharField(max_length=20, default='blue')
    
    def __str__(self):
        return self.nom
    
    class Meta:
        verbose_name = 'Catégorie de maison'
        verbose_name_plural = 'Catégories de maisons'


# CORRECTION PRINCIPALE - QuerySet et Manager personnalisés
class MaisonQuerySet(models.QuerySet):
    """QuerySet personnalisé avec les méthodes d'optimisation"""
    
    def with_photos_and_reservations(self):
        """Optimisation des requêtes avec relations"""
        return self.select_related('ville', 'categorie', 'gestionnaire').prefetch_related(
            'photos',
            'reservations__client'
        )
    
    def accessible_to_user(self, user):
        """Filtre les maisons selon les permissions utilisateur"""
        if user.is_anonymous:
            return self.filter(disponible=True)
        
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            return self
        elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
            return self.filter(gestionnaire=user)
        elif hasattr(user, 'is_client') and user.is_client():
            return self.filter(disponible=True)
        elif user.is_superuser:
            return self
        return self.filter(disponible=True)
    
    def available_for_clients(self):
        """Maisons disponibles pour les clients"""
        return self.filter(disponible=True)


class MaisonManager(models.Manager):
    """Manager personnalisé pour les maisons"""
    
    def get_queryset(self):
        return MaisonQuerySet(self.model, using=self._db)
    
    def with_photos_and_reservations(self):
        """Optimisation des requêtes avec relations"""
        return self.get_queryset().with_photos_and_reservations()
    
    def accessible_to_user(self, user):
        """Filtre les maisons selon les permissions utilisateur"""
        return self.get_queryset().accessible_to_user(user)
    
    def available_for_clients(self):
        """Maisons disponibles pour les clients"""
        return self.get_queryset().available_for_clients()


class Maison(models.Model):
    # Informations de base
    nom = models.CharField(max_length=200)
    description = models.TextField()
    adresse = models.CharField(max_length=255)
    ville = models.ForeignKey(Ville, on_delete=models.CASCADE)
    
    # Détails de la maison
    capacite_personnes = models.PositiveIntegerField()
    nombre_chambres = models.PositiveIntegerField()
    nombre_salles_bain = models.PositiveIntegerField()
    superficie = models.PositiveIntegerField(help_text="Superficie en m²")
    
    # Prix et disponibilité
    prix_par_nuit = models.DecimalField(max_digits=8, decimal_places=2)
    disponible = models.BooleanField(default=True)
    featured = models.BooleanField(default=False, help_text="Afficher sur la page d'accueil")
    
    # Catégorie
    categorie = models.ForeignKey(CategorieMaison, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Équipements
    wifi = models.BooleanField(default=True)
    parking = models.BooleanField(default=False)
    piscine = models.BooleanField(default=False)
    jardin = models.BooleanField(default=False)
    climatisation = models.BooleanField(default=False)
    lave_vaisselle = models.BooleanField(default=False)
    machine_laver = models.BooleanField(default=False)
    
    # Gestionnaire
    gestionnaire = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role__in': ['GESTIONNAIRE', 'SUPER_ADMIN']},
        verbose_name="Gestionnaire",
        help_text="Gestionnaire responsable de cette maison"
    )
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    # SEO
    slug = models.SlugField(unique=True, blank=True)
    
    # Manager personnalisé
    objects = MaisonManager()
    
    def __str__(self):
        return self.nom
    
    def get_absolute_url(self):
        return reverse('home:maison_detail', kwargs={'slug': self.slug})
    
    @property
    def photo_principale(self):
        photo = self.photos.filter(principale=True).first()
        return photo.image if photo else None
    
    @property
    def note_moyenne(self):
        return 0
    
    # COMPATIBILITÉ avec l'ancien code
    @property
    def proprietaire(self):
        """Compatibilité : proprietaire = gestionnaire"""
        return self.gestionnaire
    
    def save(self, *args, **kwargs):
        # Auto-génération du slug si absent
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.nom)
            self.slug = base_slug
            
            counter = 1
            while Maison.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
                
        super().save(*args, **kwargs)
    
    # Ajoutez aussi cette méthode à votre classe Maison si elle n'existe pas :
    def can_be_managed_by(self, user):
        """Vérifie si un utilisateur peut gérer cette maison"""
        if user.is_anonymous:
            return False
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            return True
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return True
        return self.gestionnaire == user

    # Ajoutez cette méthode à votre classe Reservation si elle n'existe pas :
    def can_be_managed_by(self, user):
        """Vérifie si un utilisateur peut gérer cette réservation"""
        if user.is_anonymous:
            return False
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            return True
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return True
        elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
            return self.maison.gestionnaire == user
        elif hasattr(user, 'is_client') and user.is_client():
            return self.client == user
        return False

    class Meta:
        verbose_name = 'Maison'
        verbose_name_plural = 'Maisons'
        ordering = ['-date_creation']


class PhotoMaison(models.Model):
    maison = models.ForeignKey(Maison, related_name='photos', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='maisons/photos/')
    titre = models.CharField(max_length=100, blank=True)
    principale = models.BooleanField(default=False)
    ordre = models.PositiveIntegerField(default=0)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Redimensionner l'image si nécessaire
        if self.image and hasattr(self.image, 'path'):
            try:
                img = Image.open(self.image.path)
                if img.height > 800 or img.width > 1200:
                    output_size = (1200, 800)
                    img.thumbnail(output_size, Image.LANCZOS)
                    img.save(self.image.path, optimize=True, quality=85)
            except Exception:
                pass
    
    def clean(self):
        # S'assurer qu'il n'y a qu'une seule photo principale par maison
        if self.principale:
            PhotoMaison.objects.filter(
                maison=self.maison, 
                principale=True
            ).exclude(pk=self.pk).update(principale=False)
    
    class Meta:
        verbose_name = 'Photo de maison'
        verbose_name_plural = 'Photos de maisons'
        ordering = ['ordre', 'id']


class Reservation(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('confirmee', 'Confirmée'),
        ('annulee', 'Annulée'),
        ('terminee', 'Terminée'),
    ]
    
    maison = models.ForeignKey(Maison, on_delete=models.CASCADE, related_name='reservations')
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'CLIENT'},
        verbose_name="Client",
        related_name='reservations'
    )
    
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    nombre_personnes = models.PositiveIntegerField()
    prix_total = models.DecimalField(max_digits=10, decimal_places=2)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    
    # Informations de contact
    telephone = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Réservation {self.maison.nom} - {self.client.username}"
    
    @property
    def duree_sejour(self):
        return (self.date_fin - self.date_debut).days
    
    # COMPATIBILITÉ avec l'ancien code
    @property
    def locataire(self):
        """Compatibilité : locataire = client"""
        return self.client
    
    def can_be_managed_by(self, user):
        """Vérifie si un utilisateur peut gérer cette réservation"""
        if user.is_anonymous:
            return False
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            return True
        if user.is_superuser:
            return True
        elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
            return self.maison.gestionnaire == user
        elif hasattr(user, 'is_client') and user.is_client():
            return self.client == user
        return False
    
    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        
        if self.date_debut >= self.date_fin:
            raise ValidationError("La date de début doit être antérieure à la date de fin.")
        
        if self.date_debut < timezone.now().date():
            raise ValidationError("La date de début ne peut pas être dans le passé.")
        
        # Vérifier qu'il n'y a pas de conflit avec d'autres réservations
        conflicting_reservations = Reservation.objects.filter(
            maison=self.maison,
            statut__in=['confirmee', 'en_attente']
        ).exclude(pk=self.pk)
        
        for reservation in conflicting_reservations:
            if (self.date_debut < reservation.date_fin and 
                self.date_fin > reservation.date_debut):
                raise ValidationError(
                    f"Cette période est en conflit avec une autre réservation "
                    f"({reservation.date_debut} - {reservation.date_fin})."
                )
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Réservation'
        verbose_name_plural = 'Réservations'
        ordering = ['-date_creation']
