from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, Avg, Sum
from decimal import Decimal
import uuid
from home.models import Maison


class TypeMeubleManager(models.Manager):
    """Manager optimisé pour TypeMeuble"""
    
    def with_stats(self):
        """Retourne les types avec statistiques d'utilisation"""
        return self.annotate(
            nombre_meubles=Count('meuble'),
            meubles_bon_etat=Count('meuble', filter=Q(meuble__etat='bon')),
            meubles_defectueux=Count('meuble', filter=Q(meuble__etat='defectueux'))
        )
    
    def by_category(self):
        """Groupe les types par catégorie"""
        return self.with_stats().order_by('categorie', 'nom')
    
    def most_used(self, limit=5):
        """Retourne les types les plus utilisés"""
        return self.with_stats().filter(nombre_meubles__gt=0).order_by('-nombre_meubles')[:limit]


class TypeMeuble(models.Model):
    """Types de meubles optimisés avec méthodes avancées"""
    
    CATEGORIE_CHOICES = [
        ('chambre', 'Chambre'),
        ('salon', 'Salon'),
        ('cuisine', 'Cuisine'),
        ('salle_bain', 'Salle de bain'),
        ('bureau', 'Bureau'),
        ('exterieur', 'Extérieur'),
        ('autre', 'Autre'),
    ]
    
    nom = models.CharField(max_length=50, unique=True, verbose_name="Nom du type")
    description = models.TextField(blank=True, verbose_name="Description")
    categorie = models.CharField(
        max_length=30,
        choices=CATEGORIE_CHOICES,
        default='autre',
        verbose_name="Catégorie"
    )
    icone = models.CharField(
        max_length=50, 
        default='cube', 
        help_text="Icône FontAwesome pour l'affichage"
    )
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    objects = TypeMeubleManager()
    
    def __str__(self):
        return self.nom
    
    @property
    def nombre_meubles(self):
        """Nombre de meubles utilisant ce type"""
        return self.meuble_set.count()
    
    @property
    def meubles_actifs(self):
        """Meubles actifs (non hors service)"""
        return self.meuble_set.exclude(etat='hors_service')
    
    @property
    def pourcentage_bon_etat(self):
        """Pourcentage de meubles en bon état pour ce type"""
        total = self.nombre_meubles
        if total == 0:
            return 0
        bon_etat = self.meuble_set.filter(etat='bon').count()
        return round((bon_etat / total) * 100, 1)
    
    def clean(self):
        """Validation personnalisée"""
        if self.nom:
            self.nom = self.nom.strip().title()
        
        # Vérifier que l'icône est valide (lettres, chiffres, tirets)
        if self.icone and not self.icone.replace('-', '').replace('_', '').isalnum():
            raise ValidationError("L'icône ne peut contenir que des lettres, chiffres et tirets")
    
    class Meta:
        verbose_name = 'Type de meuble'
        verbose_name_plural = 'Types de meubles'
        ordering = ['categorie', 'nom']
        indexes = [
            models.Index(fields=['categorie']),
            models.Index(fields=['nom']),
        ]


class MeubleManager(models.Manager):
    """Manager optimisé pour Meuble"""
    
    def get_queryset(self):
        """QuerySet de base avec relations préchargées"""
        return super().get_queryset().select_related('maison', 'type_meuble', 'ajoute_par')
    
    def actifs(self):
        """Meubles actifs (non hors service)"""
        return self.exclude(etat='hors_service')
    
    def by_etat(self, etat):
        """Filtrer par état"""
        return self.filter(etat=etat)
    
    def necessite_verification(self, jours=180):
        """Meubles nécessitant une vérification"""
        cutoff_date = timezone.now().date() - timezone.timedelta(days=jours)
        return self.filter(
            Q(date_derniere_verification__isnull=True) |
            Q(date_derniere_verification__lt=cutoff_date)
        )
    
    def with_photos(self):
        """Meubles avec photos"""
        return self.prefetch_related('photos')
    
    def with_stats(self):
        """Avec statistiques calculées"""
        return self.annotate(
            nb_photos=Count('photos'),
            nb_changements_etat=Count('historique_etats')
        )
    
    def by_maison(self, maison):
        """Filtrer par maison"""
        return self.filter(maison=maison)
    
    def search(self, query):
        """Recherche textuelle"""
        return self.filter(
            Q(nom__icontains=query) |
            Q(numero_serie__icontains=query) |
            Q(marque__icontains=query) |
            Q(modele__icontains=query) |
            Q(notes__icontains=query)
        )


class Meuble(models.Model):
    """Modèle optimisé pour les meubles avec fonctionnalités avancées"""
    
    ETAT_CHOICES = [
        ('bon', 'Bon état'),
        ('usage', 'État d\'usage'),
        ('defectueux', 'Défectueux'),
        ('hors_service', 'Hors service'),
    ]
    
    PIECE_CHOICES = [
        ('salon', 'Salon'),
        ('chambre_1', 'Chambre 1'),
        ('chambre_2', 'Chambre 2'),
        ('chambre_3', 'Chambre 3'),
        ('chambre_4', 'Chambre 4'),
        ('cuisine', 'Cuisine'),
        ('salle_bain', 'Salle de bain'),
        ('salle_eau', 'Salle d\'eau'),
        ('bureau', 'Bureau'),
        ('terrasse', 'Terrasse'),
        ('balcon', 'Balcon'),
        ('garage', 'Garage'),
        ('cave', 'Cave'),
        ('grenier', 'Grenier'),
        ('entree', 'Entrée'),
        ('couloir', 'Couloir'),
        ('autre', 'Autre'),
    ]
    
    # Identifiants
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100, verbose_name="Nom du meuble")
    numero_serie = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Numéro de série",
        help_text="Numéro d'identification unique du meuble"
    )
    
    # Relations
    type_meuble = models.ForeignKey(TypeMeuble, on_delete=models.CASCADE, verbose_name="Type")
    maison = models.ForeignKey(
        Maison, 
        on_delete=models.CASCADE, 
        related_name='meubles',
        verbose_name="Maison"
    )
    
    # État et condition
    etat = models.CharField(
        max_length=20, 
        choices=ETAT_CHOICES, 
        default='bon',
        verbose_name="État du meuble"
    )
    etat_precedent = models.CharField(
        max_length=20, 
        choices=ETAT_CHOICES, 
        blank=True,
        verbose_name="État précédent"
    )
    
    # Dates importantes
    date_entree = models.DateField(
        default=timezone.now,
        verbose_name="Date d'entrée"
    )
    date_derniere_verification = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Dernière vérification"
    )
    date_dernier_entretien = models.DateField(
        null=True,
        blank=True,
        verbose_name="Dernier entretien"
    )
    
    # Localisation
    piece = models.CharField(
        max_length=30,
        choices=PIECE_CHOICES,
        default='salon',
        verbose_name="Pièce"
    )
    position_details = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Détails de position",
        help_text="Ex: Coin gauche, près de la fenêtre"
    )
    
    # Informations détaillées
    marque = models.CharField(max_length=50, blank=True, verbose_name="Marque")
    modele = models.CharField(max_length=50, blank=True, verbose_name="Modèle")
    couleur = models.CharField(max_length=30, blank=True, verbose_name="Couleur")
    materiaux = models.CharField(max_length=100, blank=True, verbose_name="Matériaux")
    dimensions = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Dimensions",
        help_text="Ex: L120 x P60 x H75 cm"
    )
    poids = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Poids (kg)"
    )
    
    # Informations financières
    prix_achat = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Prix d'achat (FCFA)",
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    valeur_actuelle = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Valeur actuelle estimée (FCFA)",
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    cout_entretien_annuel = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Coût d'entretien annuel estimé (FCFA)"
    )
    
    # Garantie et assurance
    date_fin_garantie = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fin de garantie"
    )
    numero_police_assurance = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numéro de police d'assurance"
    )
    
    # Notes et observations
    notes = models.TextField(
        blank=True, 
        verbose_name="Notes et observations"
    )
    notes_internes = models.TextField(
        blank=True,
        verbose_name="Notes internes",
        help_text="Visibles uniquement par les gestionnaires"
    )
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    ajoute_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Ajouté par"
    )
    
    # Flags
    est_favori = models.BooleanField(default=False, verbose_name="Marqué comme favori")
    est_archive = models.BooleanField(default=False, verbose_name="Archivé")
    
    objects = MeubleManager()
    
    def __str__(self):
        return f"{self.nom} ({self.numero_serie}) - {self.maison.nom}"
    
    @property
    def age_en_jours(self):
        """Âge du meuble en jours"""
        return (timezone.now().date() - self.date_entree).days
    
    @property
    def age_en_mois(self):
        """Âge du meuble en mois"""
        return self.age_en_jours // 30
    
    @property
    def age_en_annees(self):
        """Âge du meuble en années"""
        return self.age_en_jours // 365
    
    @property
    def necessite_verification(self):
        """Vérifie si le meuble nécessite une vérification"""
        if not self.date_derniere_verification:
            return True
        
        delta = timezone.now().date() - self.date_derniere_verification
        return delta.days > 180
    
    @property
    def jours_depuis_verification(self):
        """Nombre de jours depuis la dernière vérification"""
        if not self.date_derniere_verification:
            return self.age_en_jours
        return (timezone.now().date() - self.date_derniere_verification).days
    
    @property
    def garantie_active(self):
        """Vérifie si la garantie est encore active"""
        if not self.date_fin_garantie:
            return False
        return self.date_fin_garantie >= timezone.now().date()
    
    @property
    def jours_garantie_restants(self):
        """Nombre de jours de garantie restants"""
        if not self.garantie_active:
            return 0
        return (self.date_fin_garantie - timezone.now().date()).days
    
    @property
    def depreciation_estimee(self):
        """Calcule la dépréciation estimée"""
        if not self.prix_achat:
            return Decimal('0')
        
        age_annees = Decimal(str(self.age_en_jours / 365))
        
        # Taux de dépréciation selon le type de meuble
        if self.type_meuble.categorie == 'salon':
            taux_annuel = Decimal('0.08')  # 8% par an
        elif self.type_meuble.categorie == 'cuisine':
            taux_annuel = Decimal('0.12')  # 12% par an
        elif self.type_meuble.categorie == 'chambre':
            taux_annuel = Decimal('0.06')  # 6% par an
        else:
            taux_annuel = Decimal('0.10')  # 10% par an par défaut
        
        # Dépréciation maximale de 80%
        taux_total = min(taux_annuel * age_annees, Decimal('0.8'))
        return self.prix_achat * taux_total
    
    @property
    def valeur_estimee_actuelle(self):
        """Valeur estimée actuelle basée sur la dépréciation"""
        if not self.prix_achat:
            return None
        return self.prix_achat - self.depreciation_estimee
    
    @property
    def score_etat(self):
        """Score numérique de l'état (pour calculs)"""
        scores = {
            'bon': 100,
            'usage': 70,
            'defectueux': 30,
            'hors_service': 0
        }
        return scores.get(self.etat, 0)
    
    @property
    def nb_changements_etat(self):
        """Nombre de changements d'état"""
        return self.historique_etats.count()
    
    @property
    def dernier_changement_etat(self):
        """Dernier changement d'état"""
        return self.historique_etats.first()
    
    def marquer_defectueux(self, notes="", user=None):
        """Marque le meuble comme défectueux avec historique"""
        ancien_etat = self.etat
        self.etat = 'defectueux'
        
        if notes:
            self.notes = f"{self.notes}\n[{timezone.now().date()}] Défectueux: {notes}".strip()
        
        self.save()
        
        # Créer l'historique
        HistoriqueEtatMeuble.objects.create(
            meuble=self,
            ancien_etat=ancien_etat,
            nouvel_etat='defectueux',
            modifie_par=user,
            motif=notes or "Marqué comme défectueux"
        )
    
    def reparer(self, notes="", cout=None, user=None):
        """Marque le meuble comme réparé"""
        ancien_etat = self.etat
        self.etat = 'bon'
        self.date_derniere_verification = timezone.now().date()
        self.date_dernier_entretien = timezone.now().date()
        
        if notes:
            self.notes = f"{self.notes}\n[{timezone.now().date()}] Réparé: {notes}".strip()
        
        self.save()
        
        # Créer l'historique
        HistoriqueEtatMeuble.objects.create(
            meuble=self,
            ancien_etat=ancien_etat,
            nouvel_etat='bon',
            modifie_par=user,
            motif=notes or "Réparation effectuée",
            cout=cout
        )
    
    def verifier_etat(self, nouvel_etat, notes="", user=None):
        """Met à jour l'état après vérification"""
        ancien_etat = self.etat
        self.etat = nouvel_etat
        self.date_derniere_verification = timezone.now().date()
        
        if notes:
            self.notes = f"{self.notes}\n[{timezone.now().date()}] Vérification ({ancien_etat} → {nouvel_etat}): {notes}".strip()
        
        self.save()
        
        # Créer l'historique si l'état a changé
        if ancien_etat != nouvel_etat:
            HistoriqueEtatMeuble.objects.create(
                meuble=self,
                ancien_etat=ancien_etat,
                nouvel_etat=nouvel_etat,
                modifie_par=user,
                motif=notes or f"Vérification: {ancien_etat} → {nouvel_etat}"
            )
    
    def calculer_cout_total_possession(self):
        """Calcule le coût total de possession"""
        cout_total = self.prix_achat or Decimal('0')
        
        # Ajouter les coûts d'entretien
        if self.cout_entretien_annuel:
            cout_total += self.cout_entretien_annuel * Decimal(str(self.age_en_annees))
        
        # Ajouter les coûts de réparation depuis l'historique
        cout_reparations = self.historique_etats.aggregate(
            total=Sum('cout')
        )['total'] or Decimal('0')
        
        cout_total += cout_reparations
        
        return cout_total
    
    def generer_numero_serie(self):
        """Génère automatiquement un numéro de série"""
        if not self.numero_serie and self.maison:
            count = self.maison.meubles.count() + 1
            self.numero_serie = f"{self.maison.numero}-M{count:03d}"
    
    def clean(self):
        """Validation personnalisée"""
        # Vérifier que la valeur actuelle n'est pas supérieure au prix d'achat
        if (self.prix_achat and self.valeur_actuelle and 
            self.valeur_actuelle > self.prix_achat):
            raise ValidationError(
                "La valeur actuelle ne peut pas être supérieure au prix d'achat."
            )
        
        # Vérifier que les dates sont cohérentes
        if (self.date_fin_garantie and 
            self.date_fin_garantie < self.date_entree):
            raise ValidationError(
                "La date de fin de garantie ne peut pas être antérieure à la date d'entrée."
            )
        
        # Nettoyer les champs texte
        if self.nom:
            self.nom = self.nom.strip()
        if self.marque:
            self.marque = self.marque.strip().title()
        if self.modele:
            self.modele = self.modele.strip()
    
    def save(self, *args, **kwargs):
        """Override save pour ajouter de la logique"""
        # Générer le numéro de série si nécessaire
        if not self.numero_serie:
            self.generer_numero_serie()
        
        # Sauvegarder l'état précédent
        if self.pk:
            try:
                old_instance = Meuble.objects.get(pk=self.pk)
                if old_instance.etat != self.etat:
                    self.etat_precedent = old_instance.etat
            except Meuble.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Meuble'
        verbose_name_plural = 'Meubles'
        ordering = ['maison', 'piece', 'type_meuble', 'nom']
        indexes = [
            models.Index(fields=['maison', 'etat']),
            models.Index(fields=['numero_serie']),
            models.Index(fields=['type_meuble']),
            models.Index(fields=['date_derniere_verification']),
            models.Index(fields=['etat', 'piece']),
            models.Index(fields=['date_entree']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(prix_achat__gte=0),
                name='prix_achat_positif'
            ),
            models.CheckConstraint(
                check=Q(valeur_actuelle__gte=0),
                name='valeur_actuelle_positive'
            ),
        ]


class HistoriqueEtatMeuble(models.Model):
    """Historique optimisé des changements d'état"""
    
    meuble = models.ForeignKey(
        Meuble, 
        on_delete=models.CASCADE, 
        related_name='historique_etats'
    )
    ancien_etat = models.CharField(max_length=20, choices=Meuble.ETAT_CHOICES)
    nouvel_etat = models.CharField(max_length=20, choices=Meuble.ETAT_CHOICES)
    date_changement = models.DateTimeField(auto_now_add=True)
    
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    motif = models.TextField(blank=True, verbose_name="Motif du changement")
    cout = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Coût (FCFA)"
    )
    
    # Détails de l'intervention
    intervenant = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Intervenant/Réparateur"
    )
    duree_intervention = models.DurationField(
        null=True,
        blank=True,
        verbose_name="Durée de l'intervention"
    )
    
    def __str__(self):
        return f"{self.meuble.nom}: {self.ancien_etat} → {self.nouvel_etat}"
    
    @property
    def est_amelioration(self):
        """Vérifie si le changement est une amélioration"""
        scores = {'bon': 4, 'usage': 3, 'defectueux': 2, 'hors_service': 1}
        return scores.get(self.nouvel_etat, 0) > scores.get(self.ancien_etat, 0)
    
    @property
    def est_degradation(self):
        """Vérifie si le changement est une dégradation"""
        scores = {'bon': 4, 'usage': 3, 'defectueux': 2, 'hors_service': 1}
        return scores.get(self.nouvel_etat, 0) < scores.get(self.ancien_etat, 0)
    
    class Meta:
        verbose_name = 'Historique d\'état'
        verbose_name_plural = 'Historiques d\'états'
        ordering = ['-date_changement']
        indexes = [
            models.Index(fields=['meuble', '-date_changement']),
            models.Index(fields=['date_changement']),
            models.Index(fields=['ancien_etat', 'nouvel_etat']),
        ]


class PhotoMeuble(models.Model):
    """Photos optimisées des meubles"""
    
    TYPE_PHOTO_CHOICES = [
        ('etat_general', 'État général'),
        ('detail', 'Détail'),
        ('defaut', 'Défaut/problème'),
        ('reparation', 'Après réparation'),
        ('installation', 'Installation'),
        ('entretien', 'Entretien'),
    ]
    
    meuble = models.ForeignKey(
        Meuble, 
        on_delete=models.CASCADE, 
        related_name='photos'
    )
    image = models.ImageField(
        upload_to='meubles/photos/%Y/%m/',
        verbose_name="Image"
    )
    titre = models.CharField(max_length=100, blank=True, verbose_name="Titre")
    type_photo = models.CharField(
        max_length=20,
        choices=TYPE_PHOTO_CHOICES,
        default='etat_general',
        verbose_name="Type de photo"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description détaillée"
    )
    date_prise = models.DateTimeField(auto_now_add=True)
    
    # Métadonnées techniques
    taille_fichier = models.PositiveIntegerField(null=True, blank=True)
    largeur = models.PositiveIntegerField(null=True, blank=True)
    hauteur = models.PositiveIntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"Photo {self.meuble.nom} - {self.get_type_photo_display()}"
    
    def save(self, *args, **kwargs):
        """Override save pour extraire métadonnées"""
        if self.image:
            self.taille_fichier = self.image.size
            
            # Extraire dimensions si possible
            try:
                from PIL import Image
                with Image.open(self.image) as img:
                    self.largeur, self.hauteur = img.size
            except:
                pass
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Photo de meuble'
        verbose_name_plural = 'Photos de meubles'
        ordering = ['-date_prise']
        indexes = [
            models.Index(fields=['meuble', '-date_prise']),
            models.Index(fields=['type_photo']),
        ]


class InventaireMaisonManager(models.Manager):
    """Manager pour InventaireMaison"""
    
    def with_stats(self):
        """Ajoute les statistiques calculées"""
        return self.select_related('maison', 'effectue_par')
    
    def recent(self, jours=30):
        """Inventaires récents"""
        cutoff = timezone.now() - timezone.timedelta(days=jours)
        return self.filter(date_inventaire__gte=cutoff)


class InventaireMaison(models.Model):
    """Inventaire optimisé d'une maison"""
    
    TYPE_INVENTAIRE_CHOICES = [
        ('entree', 'État des lieux d\'entrée'),
        ('sortie', 'État des lieux de sortie'),
        ('periodique', 'Inventaire périodique'),
        ('maintenance', 'Inventaire maintenance'),
        ('assurance', 'Inventaire assurance'),
        ('contentieux', 'Inventaire contentieux'),
    ]
    
    maison = models.ForeignKey(
        Maison, 
        on_delete=models.CASCADE, 
        related_name='inventaires'
    )
    date_inventaire = models.DateTimeField(auto_now_add=True)
    
    effectue_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Effectué par"
    )
    
    type_inventaire = models.CharField(
        max_length=20,
        choices=TYPE_INVENTAIRE_CHOICES,
        default='periodique',
        verbose_name="Type d'inventaire"
    )
    
    # Statistiques
    nombre_meubles_total = models.PositiveIntegerField(default=0)
    nombre_meubles_bon_etat = models.PositiveIntegerField(default=0)
    nombre_meubles_usage = models.PositiveIntegerField(default=0)
    nombre_meubles_defectueux = models.PositiveIntegerField(default=0)
    nombre_meubles_hors_service = models.PositiveIntegerField(default=0)
    
    # Valeurs financières
    valeur_totale_estimee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Valeur totale estimée (FCFA)"
    )
    
    observations = models.TextField(blank=True, verbose_name="Observations générales")
    
    # Validation et signatures
    valide_par_gestionnaire = models.BooleanField(default=False)
    date_validation = models.DateTimeField(null=True, blank=True)
    signature_locataire = models.TextField(
        blank=True,
        help_text="Signature numérique ou confirmation du locataire"
    )
    
    objects = InventaireMaisonManager()
    
    def __str__(self):
        return f"Inventaire {self.maison.nom} - {self.date_inventaire.strftime('%d/%m/%Y')}"
    
    def calculer_statistiques(self):
        """Recalcule toutes les statistiques"""
        meubles = self.maison.meubles.all()
        
        self.nombre_meubles_total = meubles.count()
        self.nombre_meubles_bon_etat = meubles.filter(etat='bon').count()
        self.nombre_meubles_usage = meubles.filter(etat='usage').count()
        self.nombre_meubles_defectueux = meubles.filter(etat='defectueux').count()
        self.nombre_meubles_hors_service = meubles.filter(etat='hors_service').count()
        
        # Calculer la valeur totale
        valeur_totale = meubles.aggregate(
            total=Sum('valeur_actuelle')
        )['total']
        
        if valeur_totale:
            self.valeur_totale_estimee = valeur_totale
        
        self.save()
    
    @property
    def pourcentage_bon_etat(self):
        """Pourcentage de meubles en bon état"""
        if self.nombre_meubles_total == 0:
            return 0
        return round((self.nombre_meubles_bon_etat / self.nombre_meubles_total) * 100, 1)
    
    @property
    def pourcentage_defectueux(self):
        """Pourcentage de meubles défectueux"""
        if self.nombre_meubles_total == 0:
            return 0
        return round((self.nombre_meubles_defectueux / self.nombre_meubles_total) * 100, 1)
    
    @property
    def score_qualite(self):
        """Score de qualité global (0-100)"""
        if self.nombre_meubles_total == 0:
            return 0
        
        score = (
            (self.nombre_meubles_bon_etat * 100) +
            (self.nombre_meubles_usage * 70) +
            (self.nombre_meubles_defectueux * 30) +
            (self.nombre_meubles_hors_service * 0)
        ) / self.nombre_meubles_total
        
        return round(score, 1)
    
    def valider(self, user):
        """Valide l'inventaire"""
        self.valide_par_gestionnaire = True
        self.date_validation = timezone.now()
        self.save()
    
    class Meta:
        verbose_name = 'Inventaire de maison'
        verbose_name_plural = 'Inventaires de maisons'
        ordering = ['-date_inventaire']
        indexes = [
            models.Index(fields=['maison', '-date_inventaire']),
            models.Index(fields=['type_inventaire']),
            models.Index(fields=['date_inventaire']),
        ]