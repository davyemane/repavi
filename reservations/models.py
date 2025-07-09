# reservations/models.py - Modèles corrigés avec PositiveIntegerField

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
import string
import random
from decimal import Decimal

from home.models import Maison


class TypePaiement(models.Model):
    """Types de paiement acceptés"""
    nom = models.CharField(max_length=50, unique=True, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    actif = models.BooleanField(default=True, verbose_name="Actif")
    frais_pourcentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        help_text="Frais en pourcentage (ex: 2.5 pour 2.5%)",
        verbose_name="Frais (%)"
    )
    frais_fixe = models.PositiveIntegerField(
        default=0,
        help_text="Frais fixe en FCFA",
        verbose_name="Frais fixe (FCFA)"
    )
    icone = models.CharField(max_length=50, default='credit-card', verbose_name="Icône")
    couleur = models.CharField(max_length=20, default='blue', verbose_name="Couleur")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nom

    @property
    def frais_total_exemple(self):
        """Exemple de frais pour 100 000 FCFA"""
        return self.calculer_frais(100000)

    def calculer_frais(self, montant):
        """Calcule les frais pour un montant donné"""
        frais_pct = int((montant * self.frais_pourcentage / 100))
        return frais_pct + self.frais_fixe

    @staticmethod
    def creer_paiements_defaut():
        paiements_defaut = [
            {
                "nom": "Mobile Money",
                "description": "Paiement via MTN ou Orange Money",
                "frais_pourcentage": Decimal('1.5'),
                "frais_fixe": 100,
                "icone": "smartphone",
                "couleur": "yellow"
            },
            {
                "nom": "Carte bancaire",
                "description": "Paiement par carte VISA ou MasterCard",
                "frais_pourcentage": Decimal('2.5'),
                "frais_fixe": 200,
                "icone": "credit-card",
                "couleur": "blue"
            },
            {
                "nom": "Espèces",
                "description": "Paiement en espèces à l'arrivée",
                "frais_pourcentage": 0,
                "frais_fixe": 0,
                "icone": "cash",
                "couleur": "gray"
            },
            {
                "nom": "Virement bancaire",
                "description": "Virement sur notre compte bancaire",
                "frais_pourcentage": 0,
                "frais_fixe": 0,
                "icone": "bank",
                "couleur": "green"
            },
            {
                "nom": "Paiement en ligne",
                "description": "Paiement sécurisé par passerelle en ligne",
                "frais_pourcentage": Decimal('2.0'),
                "frais_fixe": 150,
                "icone": "globe",
                "couleur": "purple"
            },
        ]
        for data in paiements_defaut:
            TypePaiement.objects.get_or_create(nom=data["nom"], defaults=data)

    class Meta:
        verbose_name = 'Type de paiement'
        verbose_name_plural = 'Types de paiement'
        ordering = ['nom']


class ReservationQuerySet(models.QuerySet):
    """QuerySet personnalisé pour les réservations"""
    
    def for_user(self, user):
        """Réservations accessibles à un utilisateur"""
        if user.is_anonymous:
            return self.none()
        
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            return self
        elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
            return self.filter(maison__gestionnaire=user)
        elif hasattr(user, 'is_client') and user.is_client():
            return self.filter(client=user)
        elif user.is_superuser:
            return self
        return self.none()
    
    def actives(self):
        """Réservations actives (en attente ou confirmées)"""
        return self.filter(statut__in=['en_attente', 'confirmee'])
    
    def confirmees(self):
        """Réservations confirmées uniquement"""
        return self.filter(statut='confirmee')
    
    def en_attente(self):
        """Réservations en attente"""
        return self.filter(statut='en_attente')
    
    def terminees(self):
        """Réservations terminées"""
        return self.filter(statut='terminee')
    
    def annulees(self):
        """Réservations annulées"""
        return self.filter(statut='annulee')
    
    def pour_periode(self, date_debut, date_fin):
        """Réservations pour une période donnée"""
        return self.filter(
            date_debut__lte=date_fin,
            date_fin__gte=date_debut
        ).exclude(statut='annulee')
    
    def avec_conflits(self, maison, date_debut, date_fin, exclude_id=None):
        """Réservations en conflit avec une période pour une maison"""
        queryset = self.filter(
            maison=maison,
            date_debut__lt=date_fin,
            date_fin__gt=date_debut
        ).exclude(statut='annulee')
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        
        return queryset
    
    def revenus_periode(self, date_debut, date_fin):
        """Calcul des revenus pour une période"""
        return self.filter(
            date_creation__gte=date_debut,
            date_creation__lte=date_fin,
            statut='confirmee'
        ).aggregate(
            total=models.Sum('prix_total'),
            count=models.Count('id')
        )


class ReservationManager(models.Manager):
    """Manager personnalisé pour les réservations"""
    
    def get_queryset(self):
        return ReservationQuerySet(self.model, using=self._db)
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)
    
    def actives(self):
        return self.get_queryset().actives()
    
    def confirmees(self):
        return self.get_queryset().confirmees()
    
    def generate_numero(self):
        """Génère un numéro de réservation unique"""
        while True:
            # Format: REV-YYYYMM-XXXX (ex: REV-202312-A5B7)
            year_month = timezone.now().strftime('%Y%m')
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            numero = f"REV-{year_month}-{code}"
            
            if not self.filter(numero=numero).exists():
                return numero
    
    def verifier_disponibilite(self, maison, date_debut, date_fin, exclude_id=None):
        """Vérifie la disponibilité d'une maison pour une période"""
        conflits = self.get_queryset().avec_conflits(
            maison=maison,
            date_debut=date_debut,
            date_fin=date_fin,
            exclude_id=exclude_id
        )
        return not conflits.exists()


class Reservation(models.Model):
    """Modèle principal des réservations"""
    
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('confirmee', 'Confirmée'),
        ('annulee', 'Annulée'),
        ('terminee', 'Terminée'),
    ]
    
    MODE_PAIEMENT_CHOICES = [
        ('integral', 'Paiement intégral'),
        ('acompte', 'Acompte (30%)'),
        ('echelonne', 'Paiement échelonné'),
    ]
    
    # Informations principales
    numero = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Numéro de réservation",
        help_text="Généré automatiquement"
    )
    
    # Relations
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations',
        limit_choices_to={'role': 'CLIENT'},
        verbose_name="Client"
    )
    
    maison = models.ForeignKey(
        Maison,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name="Maison"
    )
    
    # Dates et durée
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    heure_arrivee = models.TimeField(
        null=True, 
        blank=True,
        help_text="Heure d'arrivée prévue",
        verbose_name="Heure d'arrivée"
    )
    heure_depart = models.TimeField(
        null=True, 
        blank=True,
        help_text="Heure de départ prévue",
        verbose_name="Heure de départ"
    )
    
    # Détails du séjour
    nombre_personnes = models.PositiveIntegerField(verbose_name="Nombre de personnes")
    nombre_nuits = models.PositiveIntegerField(
        editable=False,
        verbose_name="Nombre de nuits"
    )
    
    # Statut et état
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente',
        verbose_name="Statut"
    )
    
    # Pricing - CHANGÉ EN POSITIVEINTEGERFIELD
    prix_par_nuit = models.PositiveIntegerField(verbose_name="Prix par nuit (FCFA)")
    
    # Frais et réductions - CHANGÉ EN POSITIVEINTEGERFIELD
    frais_service = models.PositiveIntegerField(verbose_name="Frais de service (FCFA)", default=0)
    reduction_montant = models.PositiveIntegerField(verbose_name="Montant de la réduction (FCFA)", default=0)
    
    reduction_raison = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Raison de la réduction"
    )
    
    # Totaux - CHANGÉ EN POSITIVEINTEGERFIELD
    sous_total = models.PositiveIntegerField(
        verbose_name="Sous-total (FCFA)",
        default=0
    )

    prix_total = models.PositiveIntegerField(verbose_name="Prix total (FCFA)")

    # Paiement - CHANGÉ EN POSITIVEINTEGERFIELD
    mode_paiement = models.CharField(
        max_length=20,
        choices=MODE_PAIEMENT_CHOICES,
        default='integral',
        verbose_name="Mode de paiement"
    )
    
    montant_acompte = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Montant de l'acompte (FCFA)"
    )
    
    # Informations complémentaires
    commentaire_client = models.TextField(
        blank=True,
        verbose_name="Commentaire du client",
        help_text="Demandes spéciales, remarques..."
    )
    
    commentaire_gestionnaire = models.TextField(
        blank=True,
        verbose_name="Notes du gestionnaire",
        help_text="Notes internes, instructions..."
    )
    
    # Contacts d'urgence
    contact_urgence_nom = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Contact d'urgence - Nom"
    )
    
    contact_urgence_telephone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Contact d'urgence - Téléphone"
    )
    
    # Annulation
    date_annulation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'annulation"
    )
    
    raison_annulation = models.TextField(
        blank=True,
        verbose_name="Raison de l'annulation"
    )
    
    annulee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations_annulees',
        verbose_name="Annulée par"
    )
    
    # Suivi et automatisations
    rappel_envoye = models.BooleanField(
        default=False,
        verbose_name="Rappel envoyé"
    )
    
    evaluation_demandee = models.BooleanField(
        default=False,
        verbose_name="Évaluation demandée"
    )
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    # IP et infos de création
    ip_creation = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP de création"
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )
    
    # Manager personnalisé
    objects = ReservationManager()
    
    def __str__(self):
        return f"{self.numero} - {self.client.first_name} - {self.maison.nom}"
    
    def save(self, *args, **kwargs):
        # Stocker l'ancien statut pour la gestion d'occupation
        ancien_statut = None
        if self.pk:
            try:
                old_instance = Reservation.objects.get(pk=self.pk)
                ancien_statut = old_instance.statut
            except Reservation.DoesNotExist:
                pass
        
        # Générer le numéro si nouveau
        if not self.numero:
            self.numero = Reservation.objects.generate_numero()
        
        # Calculer le nombre de nuits
        if self.date_debut and self.date_fin:
            self.nombre_nuits = (self.date_fin - self.date_debut).days
        
        # Calculer les prix si pas déjà définis
        if not self.prix_par_nuit and self.maison:
            self.prix_par_nuit = self.maison.prix_par_nuit
        
        # Calculer les totaux
        self._calculer_totaux()
        
        # Sauvegarder d'abord
        super().save(*args, **kwargs)
        
        # Gérer l'occupation APRÈS la sauvegarde
        if self.maison:
            self._gerer_occupation_maison(ancien_statut)

    def clean(self):
        """Validation personnalisée"""
        errors = {}
        
        # Vérifier les dates
        if self.date_debut and self.date_fin:
            if self.date_debut >= self.date_fin:
                errors['date_fin'] = "La date de fin doit être après la date de début."
            
            if self.date_debut < timezone.now().date():
                errors['date_debut'] = "La date de début ne peut pas être dans le passé."
            
            # Durée minimum et maximum
            duree = (self.date_fin - self.date_debut).days
            if duree < 1:
                errors['date_fin'] = "La réservation doit durer au moins 1 nuit."
            elif duree > 365:
                errors['date_fin'] = "La réservation ne peut pas dépasser 1 an."
        
        # Vérifier la capacité SEULEMENT si maison est définie
        if hasattr(self, 'maison') and self.maison and self.nombre_personnes:
            if self.nombre_personnes > self.maison.capacite_personnes:
                errors['nombre_personnes'] = f"Le nombre de personnes ne peut pas dépasser la capacité de la maison ({self.maison.capacite_personnes})."
        
        # Vérifier la disponibilité SEULEMENT si maison est définie
        if hasattr(self, 'maison') and self.maison and self.date_debut and self.date_fin:
            if not Reservation.objects.verifier_disponibilite(
                self.maison, 
                self.date_debut, 
                self.date_fin, 
                exclude_id=self.pk
            ):
                errors['__all__'] = "Cette maison n'est pas disponible pour ces dates."
        
        # Vérifier que la maison est disponible à la location SEULEMENT si maison est définie
        if hasattr(self, 'maison') and self.maison and not self.maison.disponible:
            errors['maison'] = "Cette maison n'est pas disponible à la location."
        
        # Vérifier le mode de paiement et l'acompte
        if self.mode_paiement == 'acompte' and not self.montant_acompte:
            errors['montant_acompte'] = "Le montant de l'acompte est requis pour ce mode de paiement."
        
        if errors:
            raise ValidationError(errors)

    
    def _calculer_totaux(self):
        """Calcule les totaux de la réservation - ADAPTÉ POUR ENTIERS"""
        if self.prix_par_nuit and self.nombre_nuits:
            self.sous_total = self.prix_par_nuit * self.nombre_nuits
            
            # Appliquer la réduction
            total_apres_reduction = self.sous_total - self.reduction_montant
            
            # Ajouter les frais de service
            self.prix_total = total_apres_reduction + self.frais_service
            
            # Calculer l'acompte si nécessaire (30%)
            if self.mode_paiement == 'acompte' and not self.montant_acompte:
                self.montant_acompte = int(self.prix_total * 0.30)
    
    def _gerer_occupation_maison(self, ancien_statut):
        """Gère l'occupation de la maison selon le statut"""
        try:
            if self.statut == 'confirmee' and ancien_statut != 'confirmee':
                # Réservation confirmée -> occuper la maison
                self.maison.occuper_maison(self.client, self.date_fin)
                print(f"🏠 Maison {self.maison.nom} occupée par {self.client.get_full_name()}")
                
            elif self.statut == 'terminee' and ancien_statut == 'confirmee':
                # Réservation terminée -> libérer la maison
                if self.maison.locataire_actuel == self.client:
                    self.maison.liberer_maison()
                    print(f"🏠 Maison {self.maison.nom} libérée")
                    
            elif self.statut == 'annulee' and ancien_statut == 'confirmee':
                # Réservation annulée -> libérer la maison si occupée par ce client
                if self.maison.locataire_actuel == self.client:
                    self.maison.liberer_maison()
                    print(f"🏠 Maison {self.maison.nom} libérée après annulation")
                    
            elif ancien_statut == 'confirmee' and self.statut not in ['confirmee', 'terminee']:
                # Statut changé de confirmé vers autre chose -> libérer
                if self.maison.locataire_actuel == self.client:
                    self.maison.liberer_maison()
                    print(f"🏠 Maison {self.maison.nom} libérée après changement de statut")
                    
        except Exception as e:
            print(f"⚠️ Erreur gestion occupation: {e}")
            # Ne pas lever d'exception pour ne pas bloquer la sauvegarde
    
    def get_absolute_url(self):
        return reverse('reservations:detail', kwargs={'numero': self.numero})
    
    # Propriétés calculées
    @property
    def duree_sejour(self):
        """Durée du séjour en jours"""
        return self.nombre_nuits
    
    @property
    def prix_par_personne(self):
        """Prix par personne pour tout le séjour"""
        if self.nombre_personnes > 0:
            return self.prix_total / self.nombre_personnes
        return 0
    
    @property
    def est_modifiable(self):
        """Vérifie si la réservation peut être modifiée"""
        return self.statut in ['en_attente', 'confirmee'] and self.date_debut > timezone.now().date()
    
    @property
    def est_annulable(self):
        """Vérifie si la réservation peut être annulée"""
        if self.statut in ['annulee', 'terminee']:
            return False
        
        # Ne peut pas être annulée si elle a déjà commencé
        return self.date_debut > timezone.now().date()
    
    @property
    def temps_avant_arrivee(self):
        """Temps restant avant l'arrivée"""
        if self.date_debut <= timezone.now().date():
            return None
        return (self.date_debut - timezone.now().date()).days
    
    @property
    def est_en_cours(self):
        """Vérifie si le séjour est en cours"""
        aujourd_hui = timezone.now().date()
        return (
            self.statut == 'confirmee' and 
            self.date_debut <= aujourd_hui <= self.date_fin
        )
    
    @property
    def est_entierement_paye(self):
        """Vérifie si la réservation est entièrement payée"""
        return self.montant_restant <= 0

    @property
    def montant_paye(self):
        """Montant total payé et validé"""
        try:
            return self.paiements.filter(statut='valide').aggregate(
                total=Sum('montant')
            )['total'] or 0
        except Exception:
            return 0

    @property
    def montant_restant(self):
        """Montant restant à payer"""
        return max(0, self.prix_total - self.montant_paye)
    
    @property
    def pourcentage_acompte(self):
        """Pourcentage de l'acompte par rapport au total"""
        if self.montant_acompte and self.prix_total > 0:
            return (self.montant_acompte / self.prix_total) * 100
        return 0
    
    # Méthodes d'action
    def confirmer(self, user=None):
        """Confirme la réservation et occupe automatiquement la maison"""
        if self.statut != 'en_attente':
            raise ValidationError("Seules les réservations en attente peuvent être confirmées.")
        
        # Vérifier encore une fois la disponibilité
        if not Reservation.objects.verifier_disponibilite(
            self.maison, 
            self.date_debut, 
            self.date_fin, 
            exclude_id=self.pk
        ):
            raise ValidationError("Cette maison n'est plus disponible pour ces dates.")
        
        self.statut = 'confirmee'
        self.save()
        
        # NOUVELLE LOGIQUE: Occuper automatiquement la maison
        try:
            self.maison.occuper_maison(self.client, self.date_fin)
            print(f"✅ Maison {self.maison.nom} occupée par {self.client.get_full_name()}")
        except Exception as e:
            print(f"⚠️ Erreur lors de l'occupation de la maison: {e}")
            # Ne pas lever d'exception pour ne pas bloquer la confirmation
        
        return True    
    
    def terminer(self):
        """Termine la réservation et libère automatiquement la maison"""
        if self.statut != 'confirmee':
            raise ValidationError("Seules les réservations confirmées peuvent être terminées.")
        
        # Vérifier que la date de fin est passée ou proche
        from django.utils import timezone
        today = timezone.now().date()
        if self.date_fin > today + timedelta(days=1):
            raise ValidationError("Impossible de terminer une réservation dont la date de fin n'est pas encore arrivée.")
        
        self.statut = 'terminee'
        self.save()
        
        # NOUVELLE LOGIQUE: Libérer automatiquement la maison
        try:
            # Vérifier que c'est bien ce client qui occupe la maison
            if (self.maison.locataire_actuel == self.client and 
                self.maison.statut_occupation == 'occupe'):
                self.maison.liberer_maison()
                print(f"✅ Maison {self.maison.nom} libérée après fin de séjour")
        except Exception as e:
            print(f"⚠️ Erreur lors de la libération de la maison: {e}")
        
        return True

    def annuler(self, raison, user=None):
        """Annule la réservation et libère la maison si nécessaire"""
        if not self.est_annulable:
            raise ValidationError("Cette réservation ne peut pas être annulée.")
        
        ancien_statut = self.statut
        
        self.statut = 'annulee'
        self.date_annulation = timezone.now()
        self.raison_annulation = raison
        self.annulee_par = user
        self.save()
        
        # NOUVELLE LOGIQUE: Libérer la maison si elle était occupée par ce client
        try:
            if (ancien_statut == 'confirmee' and 
                self.maison.locataire_actuel == self.client and 
                self.maison.statut_occupation == 'occupe'):
                self.maison.liberer_maison()
                print(f"✅ Maison {self.maison.nom} libérée après annulation")
        except Exception as e:
            print(f"⚠️ Erreur lors de la libération de la maison: {e}")
        
        return True

    def can_be_managed_by(self, user):
        """Vérifie si un utilisateur peut gérer cette réservation"""
        if user.is_anonymous:
            return False
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            return True
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return True
        if hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
            return self.maison.gestionnaire == user
        return self.client == user
    
    class Meta:
        verbose_name = 'Réservation'
        verbose_name_plural = 'Réservations'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['numero']),
            models.Index(fields=['client']),
            models.Index(fields=['maison']),
            models.Index(fields=['statut']),
            models.Index(fields=['date_debut', 'date_fin']),
            models.Index(fields=['date_creation']),
        ]
        
        constraints = [
            models.CheckConstraint(
                check=models.Q(date_fin__gt=models.F('date_debut')),
                name='date_fin_after_date_debut'
            ),
            models.CheckConstraint(
                check=models.Q(nombre_personnes__gte=1),
                name='nombre_personnes_positive'
            ),
            models.CheckConstraint(
                check=models.Q(prix_par_nuit__gte=0),
                name='prix_par_nuit_positive'
            ),
        ]


class Paiement(models.Model):
    """Modèle pour les paiements liés aux réservations"""
    
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('valide', 'Validé'),
        ('echec', 'Échec'),
        ('rembourse', 'Remboursé'),
    ]
    
    # Relations
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='paiements',
        verbose_name="Réservation"
    )
    
    type_paiement = models.ForeignKey(
        TypePaiement,
        on_delete=models.PROTECT,
        verbose_name="Type de paiement"
    )
    
    # Informations du paiement - CHANGÉ EN POSITIVEINTEGERFIELD
    numero_transaction = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Numéro de transaction"
    )
    
    montant = models.PositiveIntegerField(
        verbose_name="Montant (FCFA)"
    )
    
    frais = models.PositiveIntegerField(
        default=0,
        verbose_name="Frais (FCFA)"
    )
    
    montant_net = models.PositiveIntegerField(
        verbose_name="Montant net (FCFA)",
        default=0
    )
    
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente',
        verbose_name="Statut"
    )
    
    # Détails techniques
    reference_externe = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Référence externe",
        help_text="Référence du système de paiement externe"
    )
    
    reponse_gateway = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Réponse du gateway",
        help_text="Réponse complète du système de paiement"
    )
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    date_echec = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name="Notes internes"
    )
    
    def save(self, *args, **kwargs):
        # Générer numéro de transaction si nouveau
        if not self.numero_transaction:
            self.numero_transaction = self._generate_transaction_number()
        
        # Calculer les frais
        if not self.frais and self.type_paiement:
            self.frais = self.type_paiement.calculer_frais(self.montant)
        
        # Calculer le montant net
        self.montant_net = self.montant - self.frais
        
        # Gérer les dates selon le statut
        if self.statut == 'valide' and not self.date_validation:
            self.date_validation = timezone.now()
        elif self.statut == 'echec' and not self.date_echec:
            self.date_echec = timezone.now()
        
        super().save(*args, **kwargs)
    
    def _generate_transaction_number(self):
        """Génère un numéro de transaction unique"""
        while True:
            numero = f"PAY-{timezone.now().strftime('%Y%m%d')}-{random.randint(100000, 999999)}"
            if not Paiement.objects.filter(numero_transaction=numero).exists():
                return numero
    
    def __str__(self):
        return f"{self.numero_transaction} - {self.montant} FCFA - {self.get_statut_display()}"
    
    def valider(self, reference_externe="", notes=""):
        """Valide le paiement"""
        self.statut = 'valide'
        self.date_validation = timezone.now()
        if reference_externe:
            self.reference_externe = reference_externe
        if notes:
            self.notes = notes
        self.save()
    
    def marquer_echec(self, notes=""):
        """Marque le paiement comme échoué"""
        self.statut = 'echec'
        self.date_echec = timezone.now()
        if notes:
            self.notes = notes
        self.save()
    
    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['numero_transaction']),
            models.Index(fields=['reservation']),
            models.Index(fields=['statut']),
            models.Index(fields=['date_creation']),
        ]


class DisponibiliteManager(models.Manager):
    """Manager pour gérer les disponibilités"""
    
    def pour_maison_et_periode(self, maison, date_debut, date_fin):
        """Récupère les disponibilités pour une maison et une période"""
        return self.filter(
            maison=maison,
            date__gte=date_debut,
            date__lte=date_fin
        ).order_by('date')
    
    def bloquer_periode(self, maison, date_debut, date_fin, raison="Réservation"):
        """Bloque une période pour une maison"""
        dates_a_bloquer = []
        date_courante = date_debut
        
        while date_courante <= date_fin:
            dates_a_bloquer.append(date_courante)
            date_courante += timedelta(days=1)
        
        for date in dates_a_bloquer:
            self.update_or_create(
                maison=maison,
                date=date,
                defaults={
                    'disponible': False,
                    'raison_indisponibilite': raison
                }
            )
    
    def liberer_periode(self, maison, date_debut, date_fin):
        """Libère une période pour une maison"""
        self.filter(
            maison=maison,
            date__gte=date_debut,
            date__lte=date_fin
        ).update(
            disponible=True,
            raison_indisponibilite=''
        )


class Disponibilite(models.Model):
    """Modèle pour gérer la disponibilité quotidienne des maisons"""
    
    maison = models.ForeignKey(
        Maison,
        on_delete=models.CASCADE,
        related_name='disponibilites',
        verbose_name="Maison"
    )
    
    date = models.DateField(verbose_name="Date")
    
    disponible = models.BooleanField(
        default=True,
        verbose_name="Disponible"
    )
    
    # CHANGÉ EN POSITIVEINTEGERFIELD
    prix_special = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Prix spécial (FCFA)",
        help_text="Prix spécial pour cette date (optionnel)"
    )
    
    raison_indisponibilite = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Raison de l'indisponibilité"
    )
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    # Manager personnalisé
    objects = DisponibiliteManager()
    
    def __str__(self):
        status = "Disponible" if self.disponible else "Indisponible"
        return f"{self.maison.nom} - {self.date} - {status}"
    
    @property
    def prix_effectif(self):
        """Prix effectif pour cette date"""
        return self.prix_special or self.maison.prix_par_nuit
    
    class Meta:
        verbose_name = 'Disponibilité'
        verbose_name_plural = 'Disponibilités'
        unique_together = ['maison', 'date']
        ordering = ['maison', 'date']
        indexes = [
            models.Index(fields=['maison', 'date']),
            models.Index(fields=['date', 'disponible']),
        ]


class EvaluationReservation(models.Model):
    """Évaluations des réservations par les clients"""
    
    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='evaluation',
        verbose_name="Réservation"
    )
    
    # Notes (1 à 5 étoiles)
    note_globale = models.PositiveSmallIntegerField(
        choices=[(i, f"{i} étoile{'s' if i > 1 else ''}") for i in range(1, 6)],
        verbose_name="Note globale"
    )
    
    note_proprete = models.PositiveSmallIntegerField(
        choices=[(i, f"{i} étoile{'s' if i > 1 else ''}") for i in range(1, 6)],
        verbose_name="Propreté"
    )
    
    note_equipements = models.PositiveSmallIntegerField(
        choices=[(i, f"{i} étoile{'s' if i > 1 else ''}") for i in range(1, 6)],
        verbose_name="Équipements"
    )
    
    note_emplacement = models.PositiveSmallIntegerField(
        choices=[(i, f"{i} étoile{'s' if i > 1 else ''}") for i in range(1, 6)],
        verbose_name="Emplacement"
    )
    
    note_rapport_qualite_prix = models.PositiveSmallIntegerField(
        choices=[(i, f"{i} étoile{'s' if i > 1 else ''}") for i in range(1, 6)],
        verbose_name="Rapport qualité/prix"
    )
    
    # Commentaires
    commentaire = models.TextField(
        verbose_name="Commentaire",
        help_text="Partagez votre expérience"
    )
    
    points_positifs = models.TextField(
        blank=True,
        verbose_name="Points positifs"
    )
    
    points_amelioration = models.TextField(
        blank=True,
        verbose_name="Points à améliorer"
    )
    
    # Recommandations
    recommande = models.BooleanField(
        verbose_name="Recommanderiez-vous cette maison ?"
    )
    
    reviendrait = models.BooleanField(
        verbose_name="Reviendriez-vous ?"
    )
    
    # Modération
    approuve = models.BooleanField(
        default=True,
        verbose_name="Approuvé"
    )
    
    raison_rejet = models.TextField(
        blank=True,
        verbose_name="Raison du rejet"
    )
    
    # Réponse du gestionnaire
    reponse_gestionnaire = models.TextField(
        blank=True,
        verbose_name="Réponse du gestionnaire"
    )
    
    date_reponse_gestionnaire = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de réponse"
    )
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Évaluation {self.reservation.numero} - {self.note_globale}/5"
    
    @property
    def note_moyenne(self):
        """Calcule la note moyenne de toutes les catégories"""
        notes = [
            self.note_globale,
            self.note_proprete,
            self.note_equipements,
            self.note_emplacement,
            self.note_rapport_qualite_prix
        ]
        return sum(notes) / len(notes)
    
    def save(self, *args, **kwargs):
        # Mettre à jour la date de réponse si une réponse est ajoutée
        if self.reponse_gestionnaire and not self.date_reponse_gestionnaire:
            self.date_reponse_gestionnaire = timezone.now()
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Évaluation de réservation'
        verbose_name_plural = 'Évaluations de réservations'
        ordering = ['-date_creation']