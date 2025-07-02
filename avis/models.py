# avis/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count, Q
from PIL import Image
import os

class AvisQuerySet(models.QuerySet):
    """QuerySet personnalisé pour les avis"""
    
    def published(self):
        """Avis publiés (modérés et approuvés)"""
        return self.filter(statut_moderation='approuve')
    
    def pending_moderation(self):
        """Avis en attente de modération"""
        return self.filter(statut_moderation='en_attente')
    
    def by_maison(self, maison):
        """Filtrer par maison"""
        return self.filter(maison=maison)
    
    def by_note(self, note_min=None, note_max=None):
        """Filtrer par note"""
        queryset = self
        if note_min:
            queryset = queryset.filter(note__gte=note_min)
        if note_max:
            queryset = queryset.filter(note__lte=note_max)
        return queryset
    
    def with_photos(self):
        """Avis avec photos"""
        return self.filter(photos__isnull=False).distinct()
    
    def recent(self, days=30):
        """Avis récents"""
        from django.utils import timezone
        from datetime import timedelta
        date_limite = timezone.now() - timedelta(days=days)
        return self.filter(date_creation__gte=date_limite)
    
    def with_responses(self):
        """Avis avec réponses du gestionnaire"""
        return self.filter(reponse_gestionnaire__isnull=False)


class AvisManager(models.Manager):
    """Manager personnalisé pour les avis"""
    
    def get_queryset(self):
        return AvisQuerySet(self.model, using=self._db)
    
    def published(self):
        return self.get_queryset().published()
    
    def pending_moderation(self):
        return self.get_queryset().pending_moderation()
    
    def by_maison(self, maison):
        return self.get_queryset().by_maison(maison)
    
    def with_photos(self):
        return self.get_queryset().with_photos()


# avis/models.py - Correction du modèle pour rendre les champs facultatifs

class Avis(models.Model):
    """Modèle pour les avis clients sur les maisons"""
    
    # Choix de notes (1 à 5 étoiles)
    NOTE_CHOICES = [
        (1, '1 étoile - Très décevant'),
        (2, '2 étoiles - Décevant'),
        (3, '3 étoiles - Correct'),
        (4, '4 étoiles - Bien'),
        (5, '5 étoiles - Excellent'),
    ]
    
    # Statuts de modération
    STATUT_MODERATION_CHOICES = [
        ('en_attente', 'En attente de modération'),
        ('approuve', 'Approuvé'),
        ('rejete', 'Rejeté'),
        ('signale', 'Signalé'),
    ]
    
    # Relations
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='avis_donnes',
        verbose_name="Client"
    )
    
    maison = models.ForeignKey(
        'home.Maison',
        on_delete=models.CASCADE,
        related_name='avis',
        verbose_name="Maison"
    )
    
    # Contenu de l'avis
    note = models.PositiveIntegerField(
        choices=NOTE_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Note"
    )
    
    # RENDU FACULTATIF
    titre = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Titre de l'avis",
        help_text="Résumé en quelques mots (optionnel)"
    )
    
    # RENDU FACULTATIF
    commentaire = models.TextField(
        blank=True,
        verbose_name="Commentaire",
        help_text="Partagez votre expérience détaillée (optionnel)"
    )
    
    # Modération
    statut_moderation = models.CharField(
        max_length=20,
        choices=STATUT_MODERATION_CHOICES,
        default='en_attente',
        verbose_name="Statut de modération"
    )
    
    raison_rejet = models.TextField(
        blank=True,
        verbose_name="Raison du rejet",
        help_text="Explication en cas de rejet"
    )
    
    # Réponse du gestionnaire
    reponse_gestionnaire = models.TextField(
        blank=True,
        verbose_name="Réponse du gestionnaire",
        help_text="Réponse publique du gestionnaire"
    )
    
    reponse_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reponses_avis',
        verbose_name="Réponse par"
    )
    
    date_reponse = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de réponse"
    )
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    date_moderation = models.DateTimeField(null=True, blank=True, verbose_name="Date de modération")
    modere_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='avis_moderes',
        verbose_name="Modéré par"
    )
    
    # Informations sur le séjour (optionnel)
    date_sejour = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date du séjour",
        help_text="Quand avez-vous séjourné dans cette maison ?"
    )
    
    duree_sejour = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Durée du séjour (jours)",
        help_text="Combien de nuits avez-vous passées ?"
    )
    
    # Recommandation
    recommande = models.BooleanField(
        default=True,
        verbose_name="Recommande cette maison",
        help_text="Recommanderiez-vous cette maison à d'autres voyageurs ?"
    )
    
    # Statistiques d'utilité
    nombre_likes = models.PositiveIntegerField(default=0, verbose_name="Nombre de likes")
    nombre_signalements = models.PositiveIntegerField(default=0, verbose_name="Nombre de signalements")
    
    # Manager personnalisé
    objects = AvisManager()
    
    def __str__(self):
        """Représentation string sécurisée de l'avis"""
        try:
            if hasattr(self, 'client') and self.client:
                if hasattr(self.client, 'nom_complet'):
                    client_nom = self.client.nom_complet
                else:
                    client_nom = f"{self.client.first_name} {self.client.last_name}".strip()
                    if not client_nom:
                        client_nom = self.client.username
                        
                if hasattr(self, 'maison') and self.maison:
                    return f"Avis de {client_nom} - {self.maison.nom} ({self.note}★)"
                else:
                    return f"Avis de {client_nom} ({self.note}★)"
            else:
                return f"Avis #{self.pk or 'nouveau'} ({self.note}★)"
        except:
            return f"Avis #{self.pk or 'nouveau'}"
    
    @property
    def note_etoiles(self):
        """Retourne les étoiles sous forme de string"""
        return "★" * self.note + "☆" * (5 - self.note)
    
    @property
    def est_recent(self):
        """Vérifie si l'avis est récent (moins de 7 jours)"""
        from django.utils import timezone
        from datetime import timedelta
        return self.date_creation >= timezone.now() - timedelta(days=7)
    
    @property
    def peut_etre_modifie(self):
        """Vérifie si l'avis peut encore être modifié"""
        from django.utils import timezone
        from datetime import timedelta
        # Peut être modifié dans les 24h et seulement si en attente
        return (
            self.statut_moderation == 'en_attente' and
            self.date_creation >= timezone.now() - timedelta(hours=24)
        )
    
    def clean(self):
        """Validation personnalisée"""
        from django.core.exceptions import ValidationError
        
        # Vérifier que le client a le bon rôle
        if self.client and hasattr(self.client, 'is_client'):
            if not self.client.is_client():
                raise ValidationError("Seuls les clients peuvent donner des avis.")
        
        # Vérifier qu'un client ne peut donner qu'un seul avis par maison
        if self.pk is None and self.client and self.maison:  # Nouveau avis
            if Avis.objects.filter(client=self.client, maison=self.maison).exists():
                raise ValidationError("Vous avez déjà donné un avis pour cette maison.")
    
    def save(self, *args, **kwargs):
        # Ne rien faire de spécial ici pour éviter les erreurs
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Avis'
        verbose_name_plural = 'Avis'
        ordering = ['-date_creation']
        unique_together = [['client', 'maison']]  # Un seul avis par client par maison
        indexes = [
            models.Index(fields=['maison', 'statut_moderation']),
            models.Index(fields=['client']),
            models.Index(fields=['note']),
            models.Index(fields=['date_creation']),
        ]
class PhotoAvis(models.Model):
    """Photos ajoutées aux avis"""
    
    avis = models.ForeignKey(
        Avis,
        related_name='photos',
        on_delete=models.CASCADE,
        verbose_name="Avis"
    )
    
    image = models.ImageField(
        upload_to='avis/photos/',
        verbose_name="Photo"
    )
    
    legende = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Légende",
        help_text="Description de la photo"
    )
    
    ordre = models.PositiveIntegerField(
        default=0,
        verbose_name="Ordre d'affichage"
    )
    
    # Métadonnées
    date_ajout = models.DateTimeField(auto_now_add=True)
    taille_fichier = models.PositiveIntegerField(null=True, blank=True, help_text="Taille en octets")
    
    def save(self, *args, **kwargs):
        # Limiter le nombre de photos par avis (max 5)
        if self.pk is None:  # Nouvelle photo
            nb_photos = PhotoAvis.objects.filter(avis=self.avis).count()
            if nb_photos >= 5:
                raise ValueError("Maximum 5 photos par avis autorisées")
        
        # Sauvegarder d'abord
        super().save(*args, **kwargs)
        
        # Redimensionner et optimiser l'image
        if self.image and hasattr(self.image, 'path'):
            try:
                img = Image.open(self.image.path)
                
                # Enregistrer la taille du fichier
                if os.path.exists(self.image.path):
                    self.taille_fichier = os.path.getsize(self.image.path)
                
                # Redimensionner si trop grande (800x600 max pour avis)
                if img.height > 600 or img.width > 800:
                    output_size = (800, 600)
                    img.thumbnail(output_size, Image.LANCZOS)
                    img.save(self.image.path, optimize=True, quality=85)
                    
                    # Mettre à jour la taille après compression
                    if os.path.exists(self.image.path):
                        self.taille_fichier = os.path.getsize(self.image.path)
                        PhotoAvis.objects.filter(pk=self.pk).update(taille_fichier=self.taille_fichier)
                        
            except Exception as e:
                print(f"Erreur lors du traitement de l'image d'avis: {e}")
    
    def __str__(self):
        return f"Photo avis {self.avis.id} - {self.legende[:50]}"
    
    class Meta:
        verbose_name = 'Photo d\'avis'
        verbose_name_plural = 'Photos d\'avis'
        ordering = ['avis', 'ordre', 'id']


class LikeAvis(models.Model):
    """Système de likes pour les avis"""
    
    avis = models.ForeignKey(
        Avis,
        related_name='likes',
        on_delete=models.CASCADE
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['avis', 'user']]  # Un seul like par user par avis
        verbose_name = 'Like d\'avis'
        verbose_name_plural = 'Likes d\'avis'


class SignalementAvis(models.Model):
    """Signalements d'avis inappropriés"""
    
    RAISON_CHOICES = [
        ('spam', 'Spam'),
        ('faux', 'Faux avis'),
        ('inapproprie', 'Contenu inapproprié'),
        ('hors_sujet', 'Hors sujet'),
        ('insultes', 'Insultes ou menaces'),
        ('autre', 'Autre'),
    ]
    
    avis = models.ForeignKey(
        Avis,
        related_name='signalements',
        on_delete=models.CASCADE
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Signalé par"
    )
    
    raison = models.CharField(
        max_length=20,
        choices=RAISON_CHOICES,
        verbose_name="Raison du signalement"
    )
    
    commentaire = models.TextField(
        blank=True,
        verbose_name="Commentaire",
        help_text="Détails sur le signalement"
    )
    
    date_creation = models.DateTimeField(auto_now_add=True)
    traite = models.BooleanField(default=False, verbose_name="Traité")
    traite_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='signalements_traites',
        verbose_name="Traité par"
    )
    
    class Meta:
        unique_together = [['avis', 'user']]  # Un seul signalement par user par avis
        verbose_name = 'Signalement d\'avis'
        verbose_name_plural = 'Signalements d\'avis'


# Extension du modèle Maison pour les statistiques d'avis
def get_note_moyenne(self):
    """Calcule la note moyenne des avis approuvés"""
    from django.db.models import Avg
    result = self.avis.filter(statut_moderation='approuve').aggregate(
        moyenne=Avg('note')
    )
    return round(result['moyenne'] or 0, 1)

def get_nombre_avis(self):
    """Nombre total d'avis approuvés"""
    return self.avis.filter(statut_moderation='approuve').count()

def get_repartition_notes(self):
    """Répartition des notes (pour graphiques)"""
    from django.db.models import Count
    return self.avis.filter(statut_moderation='approuve').values('note').annotate(
        count=Count('note')
    ).order_by('note')

def get_avis_recents(self, limit=3):
    """Derniers avis approuvés"""
    return self.avis.filter(statut_moderation='approuve').order_by('-date_creation')[:limit]

def get_pourcentage_recommandation(self):
    """Pourcentage de clients qui recommandent"""
    total_avis = self.avis.filter(statut_moderation='approuve').count()
    if total_avis == 0:
        return 0
    
    avis_recommandes = self.avis.filter(
        statut_moderation='approuve',
        recommande=True
    ).count()
    
    return round((avis_recommandes / total_avis) * 100)

# Monkey patch pour ajouter les méthodes au modèle Maison existant
try:
    from home.models import Maison
    
    # Vérifie si les méthodes n'existent pas déjà pour éviter les conflits
    if not hasattr(Maison, 'get_note_moyenne'):
        Maison.get_note_moyenne = get_note_moyenne
    if not hasattr(Maison, 'get_nombre_avis'):
        Maison.get_nombre_avis = get_nombre_avis
    if not hasattr(Maison, 'get_repartition_notes'):
        Maison.get_repartition_notes = get_repartition_notes
    if not hasattr(Maison, 'get_avis_recents'):
        Maison.get_avis_recents = get_avis_recents
    if not hasattr(Maison, 'get_pourcentage_recommandation'):
        Maison.get_pourcentage_recommandation = get_pourcentage_recommandation
        
    print("✅ Méthodes d'avis ajoutées au modèle Maison")
    
except ImportError as e:
    print(f"⚠️ Impossible d'importer le modèle Maison: {e}")
except Exception as e:
    print(f"⚠️ Erreur lors du monkey patching: {e}")

# Mise à jour des propriétés existantes dans le modèle Maison
def note_moyenne_property(self):
    return self.get_note_moyenne()

def nombre_avis_property(self):
    return self.get_nombre_avis()

Maison.note_moyenne = property(note_moyenne_property)
Maison.nombre_avis = property(nombre_avis_property)