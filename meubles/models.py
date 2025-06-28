from django.db import models
from django.conf import settings
from django.utils import timezone
from home.models import Maison


class TypeMeuble(models.Model):
    """Types de meubles (Lit, Armoire, Table, etc.)"""
    nom = models.CharField(max_length=50, unique=True, verbose_name="Nom du type")
    description = models.TextField(blank=True, verbose_name="Description")
    categorie = models.CharField(
        max_length=30,
        choices=[
            ('chambre', 'Chambre'),
            ('salon', 'Salon'),
            ('cuisine', 'Cuisine'),
            ('salle_bain', 'Salle de bain'),
            ('exterieur', 'Extérieur'),
            ('autre', 'Autre'),
        ],
        default='autre',
        verbose_name="Catégorie"
    )
    icone = models.CharField(max_length=50, default='cube', help_text="Icône pour l'affichage")
    
    def __str__(self):
        return self.nom
    
    @property
    def nombre_meubles(self):
        return self.meuble_set.count()
    
    class Meta:
        verbose_name = 'Type de meuble'
        verbose_name_plural = 'Types de meubles'
        ordering = ['categorie', 'nom']


class Meuble(models.Model):
    """Modèle pour gérer les meubles selon le cahier des charges"""
    ETAT_CHOICES = [
        ('bon', 'Bon état'),
        ('usage', 'État d\'usage'),
        ('defectueux', 'Défectueux'),
        ('hors_service', 'Hors service'),
    ]
    
    # Informations de base
    nom = models.CharField(max_length=100, verbose_name="Nom du meuble")
    type_meuble = models.ForeignKey(TypeMeuble, on_delete=models.CASCADE, verbose_name="Type")
    numero_serie = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Numéro de série",
        help_text="Numéro d'identification unique du meuble"
    )
    
    # Association avec la maison
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
    
    # Dates importantes
    date_entree = models.DateField(
        default=timezone.now,
        verbose_name="Date d'entrée",
        help_text="Date d'acquisition ou d'installation"
    )
    date_derniere_verification = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Dernière vérification"
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
    
    # Prix et valeur
    prix_achat = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Prix d'achat (FCFA)"
    )
    valeur_actuelle = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Valeur actuelle estimée (FCFA)"
    )
    
    # Emplacement dans la maison
    piece = models.CharField(
        max_length=30,
        choices=[
            ('salon', 'Salon'),
            ('chambre_1', 'Chambre 1'),
            ('chambre_2', 'Chambre 2'),
            ('chambre_3', 'Chambre 3'),
            ('cuisine', 'Cuisine'),
            ('salle_bain', 'Salle de bain'),
            ('terrasse', 'Terrasse'),
            ('balcon', 'Balcon'),
            ('garage', 'Garage'),
            ('autre', 'Autre'),
        ],
        default='salon',
        verbose_name="Pièce"
    )
    
    # Notes et observations
    notes = models.TextField(
        blank=True, 
        verbose_name="Notes et observations",
        help_text="Remarques sur l'état, l'utilisation, les réparations, etc."
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
    
    def __str__(self):
        return f"{self.nom} ({self.numero_serie}) - {self.maison.numero}"
    
    @property
    def age_en_mois(self):
        """Âge du meuble en mois"""
        delta = timezone.now().date() - self.date_entree
        return delta.days // 30
    
    @property
    def necessite_verification(self):
        """Vérifie si le meuble nécessite une vérification"""
        if not self.date_derniere_verification:
            return True
        
        # Vérification recommandée tous les 6 mois
        delta = timezone.now().date() - self.date_derniere_verification
        return delta.days > 180
    
    @property
    def depreciation_estimee(self):
        """Calcule la dépréciation estimée"""
        if not self.prix_achat:
            return 0
        
        age_annees = self.age_en_mois / 12
        # Dépréciation de 10% par an, max 70%
        taux_depreciation = min(0.1 * age_annees, 0.7)
        return float(self.prix_achat * taux_depreciation)
    
    def marquer_defectueux(self, notes=""):
        """Marque le meuble comme défectueux"""
        self.etat = 'defectueux'
        if notes:
            self.notes = f"{self.notes}\n[{timezone.now().date()}] Défectueux: {notes}"
        self.save()
    
    def reparer(self, notes=""):
        """Marque le meuble comme réparé"""
        self.etat = 'bon'
        self.date_derniere_verification = timezone.now().date()
        if notes:
            self.notes = f"{self.notes}\n[{timezone.now().date()}] Réparé: {notes}"
        self.save()
    
    def verifier_etat(self, nouvel_etat, notes=""):
        """Met à jour l'état après vérification"""
        ancien_etat = self.etat
        self.etat = nouvel_etat
        self.date_derniere_verification = timezone.now().date()
        
        if notes:
            self.notes = f"{self.notes}\n[{timezone.now().date()}] Vérification ({ancien_etat} → {nouvel_etat}): {notes}"
        
        self.save()
    
    class Meta:
        verbose_name = 'Meuble'
        verbose_name_plural = 'Meubles'
        ordering = ['maison', 'piece', 'type_meuble', 'nom']
        indexes = [
            models.Index(fields=['maison', 'etat']),
            models.Index(fields=['numero_serie']),
            models.Index(fields=['type_meuble']),
            models.Index(fields=['date_derniere_verification']),
        ]


class HistoriqueEtatMeuble(models.Model):
    """Historique des changements d'état des meubles"""
    meuble = models.ForeignKey(
        Meuble, 
        on_delete=models.CASCADE, 
        related_name='historique_etats'
    )
    ancien_etat = models.CharField(max_length=20, choices=Meuble.ETAT_CHOICES)
    nouvel_etat = models.CharField(max_length=20, choices=Meuble.ETAT_CHOICES)
    date_changement = models.DateTimeField(auto_now_add=True)
    
    # Qui a fait le changement
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Raison du changement
    motif = models.TextField(
        blank=True,
        verbose_name="Motif du changement",
        help_text="Explication du changement d'état"
    )
    
    # Coût éventuel (réparation, remplacement)
    cout = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Coût (FCFA)",
        help_text="Coût de la réparation ou du remplacement"
    )
    
    def __str__(self):
        return f"{self.meuble.nom}: {self.ancien_etat} → {self.nouvel_etat}"
    
    class Meta:
        verbose_name = 'Historique d\'état'
        verbose_name_plural = 'Historiques d\'états'
        ordering = ['-date_changement']


class PhotoMeuble(models.Model):
    """Photos des meubles pour documentation"""
    meuble = models.ForeignKey(
        Meuble, 
        on_delete=models.CASCADE, 
        related_name='photos'
    )
    image = models.ImageField(
        upload_to='meubles/photos/',
        verbose_name="Image"
    )
    titre = models.CharField(max_length=100, blank=True, verbose_name="Titre")
    type_photo = models.CharField(
        max_length=20,
        choices=[
            ('etat_general', 'État général'),
            ('detail', 'Détail'),
            ('defaut', 'Défaut/problème'),
            ('reparation', 'Après réparation'),
        ],
        default='etat_general',
        verbose_name="Type de photo"
    )
    date_prise = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Photo {self.meuble.nom} - {self.get_type_photo_display()}"
    
    class Meta:
        verbose_name = 'Photo de meuble'
        verbose_name_plural = 'Photos de meubles'
        ordering = ['-date_prise']


class InventaireMaison(models.Model):
    """Inventaire complet d'une maison à une date donnée"""
    maison = models.ForeignKey(
        Maison, 
        on_delete=models.CASCADE, 
        related_name='inventaires'
    )
    date_inventaire = models.DateTimeField(auto_now_add=True)
    
    # Qui a fait l'inventaire
    effectue_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Effectué par"
    )
    
    # Type d'inventaire
    type_inventaire = models.CharField(
        max_length=20,
        choices=[
            ('entree', 'État des lieux d\'entrée'),
            ('sortie', 'État des lieux de sortie'),
            ('periodique', 'Inventaire périodique'),
            ('maintenance', 'Inventaire maintenance'),
        ],
        default='periodique',
        verbose_name="Type d'inventaire"
    )
    
    # Résumé
    nombre_meubles_total = models.PositiveIntegerField(default=0)
    nombre_meubles_bon_etat = models.PositiveIntegerField(default=0)
    nombre_meubles_defectueux = models.PositiveIntegerField(default=0)
    
    # Notes générales
    observations = models.TextField(
        blank=True,
        verbose_name="Observations générales"
    )
    
    # Photos générales de l'inventaire
    photos = models.ManyToManyField(
        'PhotoMeuble',
        blank=True,
        verbose_name="Photos de l'inventaire"
    )
    
    def __str__(self):
        return f"Inventaire {self.maison.numero} - {self.date_inventaire.strftime('%d/%m/%Y')}"
    
    def calculer_statistiques(self):
        """Recalcule les statistiques de l'inventaire"""
        meubles = self.maison.meubles.all()
        
        self.nombre_meubles_total = meubles.count()
        self.nombre_meubles_bon_etat = meubles.filter(etat='bon').count()
        self.nombre_meubles_defectueux = meubles.filter(etat='defectueux').count()
        
        self.save()
    
    @property
    def pourcentage_bon_etat(self):
        """Pourcentage de meubles en bon état"""
        if self.nombre_meubles_total == 0:
            return 0
        return round((self.nombre_meubles_bon_etat / self.nombre_meubles_total) * 100, 1)
    
    class Meta:
        verbose_name = 'Inventaire de maison'
        verbose_name_plural = 'Inventaires de maisons'
        ordering = ['-date_inventaire']