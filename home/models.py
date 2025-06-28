from django.db import models
from django.conf import settings
from django.urls import reverse
from PIL import Image
from django.db.models import Q, Count

class Ville(models.Model):
    nom = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    departement = models.CharField(max_length=100)
    pays = models.CharField(max_length=100, default='Cameroun')  # Adapté au projet
    
    def __str__(self):
        return f"{self.nom}, {self.departement}"
    
    class Meta:
        verbose_name = 'Ville'
        verbose_name_plural = 'Villes'
        ordering = ['nom']


class CategorieMaison(models.Model):
    nom = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    couleur = models.CharField(max_length=20, default='blue')
    icone = models.CharField(max_length=50, default='home', help_text="Icône pour l'affichage")
    
    def __str__(self):
        return self.nom
    
    @property
    def nombre_maisons(self):
        return self.maison_set.filter(disponible=True).count()
    
    class Meta:
        verbose_name = 'Catégorie de maison'
        verbose_name_plural = 'Catégories de maisons'
        ordering = ['nom']


# QuerySet et Manager personnalisés pour les maisons
class MaisonQuerySet(models.QuerySet):
    """QuerySet personnalisé avec les méthodes d'optimisation"""
    
    def with_photos_and_details(self):
        """Optimisation des requêtes avec relations"""
        return self.select_related('ville', 'categorie', 'gestionnaire').prefetch_related('photos')
    
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
        return self.filter(disponible=True, statut_occupation='libre')
    
    def by_ville(self, ville):
        """Filtrer par ville"""
        return self.filter(ville=ville)
    
    def by_categorie(self, categorie):
        """Filtrer par catégorie"""
        return self.filter(categorie=categorie)
    
    def featured(self):
        """Maisons mises en avant"""
        return self.filter(featured=True, disponible=True)


class MaisonManager(models.Manager):
    """Manager personnalisé pour les maisons"""
    
    def get_queryset(self):
        return MaisonQuerySet(self.model, using=self._db)
    
    def with_photos_and_details(self):
        return self.get_queryset().with_photos_and_details()
    
    def accessible_to_user(self, user):
        return self.get_queryset().accessible_to_user(user)
    
    def available_for_clients(self):
        return self.get_queryset().available_for_clients()
    
    def featured(self):
        return self.get_queryset().featured()


class Maison(models.Model):
    # Statuts d'occupation selon le cahier des charges
    STATUT_OCCUPATION_CHOICES = [
        ('libre', 'Libre'),
        ('occupe', 'Occupé'),
        ('maintenance', 'En maintenance'),
        ('indisponible', 'Indisponible'),
    ]
    
    # Informations de base
    nom = models.CharField(max_length=200, verbose_name="Nom de la maison")
    numero = models.CharField(max_length=10, unique=True, verbose_name="Numéro", help_text="Numéro d'identification unique")
    description = models.TextField(verbose_name="Description")
    adresse = models.CharField(max_length=255, verbose_name="Adresse")
    ville = models.ForeignKey(Ville, on_delete=models.CASCADE, verbose_name="Ville")
    
    # Détails de la maison
    capacite_personnes = models.PositiveIntegerField(verbose_name="Capacité (personnes)")
    nombre_chambres = models.PositiveIntegerField(verbose_name="Nombre de chambres")
    nombre_salles_bain = models.PositiveIntegerField(verbose_name="Nombre de salles de bain")
    superficie = models.PositiveIntegerField(help_text="Superficie en m²", verbose_name="Superficie (m²)")
    
    # Prix et disponibilité
    prix_par_nuit = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Prix par nuit (FCFA)")
    disponible = models.BooleanField(default=True, verbose_name="Disponible à la location")
    featured = models.BooleanField(default=False, help_text="Afficher sur la page d'accueil", verbose_name="Mise en avant")
    
    # Statut d'occupation (NOUVEAU selon vos besoins)
    statut_occupation = models.CharField(
        max_length=20, 
        choices=STATUT_OCCUPATION_CHOICES, 
        default='libre',
        verbose_name="Statut d'occupation"
    )
    
    # Locataire actuel (NOUVEAU)
    locataire_actuel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maisons_occupees',
        limit_choices_to={'role': 'CLIENT'},
        verbose_name="Locataire actuel"
    )
    
    # Date de fin de location (NOUVEAU)
    date_fin_location = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Date de fin de location",
        help_text="Date prévue de libération de la maison"
    )
    
    # Catégorie
    categorie = models.ForeignKey(
        CategorieMaison, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Catégorie"
    )
    
    # Équipements
    wifi = models.BooleanField(default=True, verbose_name="WiFi")
    parking = models.BooleanField(default=False, verbose_name="Parking")
    piscine = models.BooleanField(default=False, verbose_name="Piscine")
    jardin = models.BooleanField(default=False, verbose_name="Jardin")
    climatisation = models.BooleanField(default=False, verbose_name="Climatisation")
    lave_vaisselle = models.BooleanField(default=False, verbose_name="Lave-vaisselle")
    machine_laver = models.BooleanField(default=False, verbose_name="Machine à laver")
    balcon = models.BooleanField(default=False, verbose_name="Balcon")
    terrasse = models.BooleanField(default=False, verbose_name="Terrasse")
    
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
        return f"{self.numero} - {self.nom}"
    
    def get_absolute_url(self):
        return reverse('home:maison_detail', kwargs={'slug': self.slug})
    
    @property
    def photo_principale(self):
        """Récupère la photo principale de la maison"""
        photo = self.photos.filter(principale=True).first()
        return photo.image if photo else None
    
    @property
    def photos_additionnelles(self):
        """Récupère toutes les photos sauf la principale"""
        return self.photos.filter(principale=False).order_by('ordre')
    
    @property
    def note_moyenne(self):
        """Note moyenne des avis (à implémenter avec l'app avis)"""
        return 0  # TODO: calculer depuis l'app avis
    
    @property
    def nombre_avis(self):
        """Nombre total d'avis (à implémenter avec l'app avis)"""
        return 0  # TODO: compter depuis l'app avis
    
    # NOUVELLES PROPRIÉTÉS selon vos besoins
    @property
    def nombre_meubles(self):
        """Nombre total de meubles dans la maison"""
        return getattr(self, 'meubles', self.__class__.objects.none()).count()
    
    @property
    def meubles_defectueux(self):
        """Nombre de meubles défectueux"""
        return getattr(self, 'meubles', self.__class__.objects.none()).filter(etat='defectueux').count()
    
    @property
    def meubles_bon_etat(self):
        """Nombre de meubles en bon état"""
        return getattr(self, 'meubles', self.__class__.objects.none()).filter(etat='bon').count()
    
    @property
    def est_occupee(self):
        """Vérifie si la maison est actuellement occupée"""
        return self.statut_occupation == 'occupe' and self.locataire_actuel is not None
    
    @property
    def jours_restants_location(self):
        """Nombre de jours restants pour la location actuelle"""
        if self.date_fin_location:
            from django.utils import timezone
            delta = self.date_fin_location - timezone.now().date()
            return delta.days if delta.days > 0 else 0
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
            base_slug = slugify(f"{self.numero}-{self.nom}")
            self.slug = base_slug
            
            counter = 1
            while Maison.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        
        # Logique de cohérence
        if self.statut_occupation != 'occupe':
            self.locataire_actuel = None
            self.date_fin_location = None
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validation personnalisée"""
        from django.core.exceptions import ValidationError
        
        # Si occupé, doit avoir un locataire et une date de fin
        if self.statut_occupation == 'occupe':
            if not self.locataire_actuel:
                raise ValidationError("Une maison occupée doit avoir un locataire.")
            if not self.date_fin_location:
                raise ValidationError("Une maison occupée doit avoir une date de fin de location.")
        
        # Si date de fin dans le passé, mettre à jour le statut
        if self.date_fin_location:
            from django.utils import timezone
            if self.date_fin_location < timezone.now().date():
                if self.statut_occupation == 'occupe':
                    self.statut_occupation = 'libre'
                    self.locataire_actuel = None
                    self.date_fin_location = None
    
    def can_be_managed_by(self, user):
        """Vérifie si un utilisateur peut gérer cette maison"""
        if user.is_anonymous:
            return False
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            return True
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return True
        return self.gestionnaire == user
    
    def liberer_maison(self):
        """Libère la maison (fin de location)"""
        self.statut_occupation = 'libre'
        self.locataire_actuel = None
        self.date_fin_location = None
        self.save()
    
    def occuper_maison(self, locataire, date_fin):
        """Occupe la maison avec un locataire"""
        self.statut_occupation = 'occupe'
        self.locataire_actuel = locataire
        self.date_fin_location = date_fin
        self.save()
    
    class Meta:
        verbose_name = 'Maison'
        verbose_name_plural = 'Maisons'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['statut_occupation']),
            models.Index(fields=['disponible']),
            models.Index(fields=['gestionnaire']),
            models.Index(fields=['ville']),
        ]


class PhotoMaison(models.Model):
    TYPES_PHOTO_CHOICES = [
        ('exterieur', 'Extérieur'),
        ('salon', 'Salon'),
        ('chambre', 'Chambre'),
        ('cuisine', 'Cuisine'),
        ('salle_bain', 'Salle de bain'),
        ('autre', 'Autre'),
    ]
    
    maison = models.ForeignKey(Maison, related_name='photos', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='maisons/photos/', verbose_name="Image")
    titre = models.CharField(max_length=100, blank=True, verbose_name="Titre")
    type_photo = models.CharField(
        max_length=20, 
        choices=TYPES_PHOTO_CHOICES, 
        default='autre',
        verbose_name="Type de photo"
    )
    principale = models.BooleanField(default=False, verbose_name="Photo principale")
    ordre = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    
    # Métadonnées
    date_ajout = models.DateTimeField(auto_now_add=True)
    taille_fichier = models.PositiveIntegerField(null=True, blank=True, help_text="Taille en octets")
    
    def save(self, *args, **kwargs):
        # Sauvegarder d'abord pour avoir le fichier
        super().save(*args, **kwargs)
        
        # Redimensionner l'image si nécessaire
        if self.image and hasattr(self.image, 'path'):
            try:
                img = Image.open(self.image.path)
                
                # Enregistrer la taille du fichier
                import os
                if os.path.exists(self.image.path):
                    self.taille_fichier = os.path.getsize(self.image.path)
                
                # Redimensionner si trop grande
                if img.height > 800 or img.width > 1200:
                    output_size = (1200, 800)
                    img.thumbnail(output_size, Image.LANCZOS)
                    img.save(self.image.path, optimize=True, quality=85)
                    
                    # Mettre à jour la taille après compression
                    if os.path.exists(self.image.path):
                        self.taille_fichier = os.path.getsize(self.image.path)
                        PhotoMaison.objects.filter(pk=self.pk).update(taille_fichier=self.taille_fichier)
                        
            except Exception as e:
                print(f"Erreur lors du traitement de l'image: {e}")
    
    def clean(self):
        # S'assurer qu'il n'y a qu'une seule photo principale par maison
        if self.principale:
            PhotoMaison.objects.filter(
                maison=self.maison, 
                principale=True
            ).exclude(pk=self.pk).update(principale=False)
    
    def __str__(self):
        return f"Photo {self.maison.nom} - {self.get_type_photo_display()}"
    
    class Meta:
        verbose_name = 'Photo de maison'
        verbose_name_plural = 'Photos de maisons'
        ordering = ['maison', 'ordre', 'id']
        indexes = [
            models.Index(fields=['maison', 'principale']),
            models.Index(fields=['maison', 'ordre']),
        ]