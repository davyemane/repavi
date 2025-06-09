# home/models.py
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from PIL import Image

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
    couleur = models.CharField(max_length=20, default='blue')  # Pour les badges
    
    def __str__(self):
        return self.nom
    
    class Meta:
        verbose_name = 'Catégorie de maison'
        verbose_name_plural = 'Catégories de maisons'

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
    
    # Catégorie et caractéristiques
    categorie = models.ForeignKey(CategorieMaison, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Équipements
    wifi = models.BooleanField(default=True)
    parking = models.BooleanField(default=False)
    piscine = models.BooleanField(default=False)
    jardin = models.BooleanField(default=False)
    climatisation = models.BooleanField(default=False)
    lave_vaisselle = models.BooleanField(default=False)
    machine_laver = models.BooleanField(default=False)
    
    # Métadonnées
    proprietaire = models.ForeignKey(User, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    # SEO
    slug = models.SlugField(unique=True, blank=True)
    
    def __str__(self):
        return self.nom
    
    def get_absolute_url(self):
        return reverse('maison:detail', kwargs={'slug': self.slug})
    
    @property
    def photo_principale(self):
        photo = self.photos.filter(principale=True).first()
        return photo.image if photo else None
    
    @property
    def note_moyenne(self):
        avis = self.avis.all()
        if avis:
            return sum([a.note for a in avis]) / len(avis)
        return 0
    
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
        
        # Redimensionner l'image
        if self.image:
            img = Image.open(self.image.path)
            if img.height > 800 or img.width > 1200:
                output_size = (1200, 800)
                img.thumbnail(output_size)
                img.save(self.image.path)
    
    class Meta:
        verbose_name = 'Photo de maison'
        verbose_name_plural = 'Photos de maisons'
        ordering = ['ordre']

class Reservation(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('confirmee', 'Confirmée'),
        ('annulee', 'Annulée'),
        ('terminee', 'Terminée'),
    ]
    
    maison = models.ForeignKey(Maison, on_delete=models.CASCADE)
    locataire = models.ForeignKey(User, on_delete=models.CASCADE)
    date_debut = models.DateField()
    date_fin = models.DateField()
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
        return f"Réservation {self.maison.nom} - {self.locataire.username}"
    
    @property
    def duree_sejour(self):
        return (self.date_fin - self.date_debut).days
    
    class Meta:
        verbose_name = 'Réservation'
        verbose_name_plural = 'Réservations'
        ordering = ['-date_creation']