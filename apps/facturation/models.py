# ==========================================
# apps/facturation/models.py
# ==========================================
from django.db import models
from django.conf import settings
from decimal import Decimal
from datetime import datetime

class Facture(models.Model):
    """
    Modèle Facture pour RepAvi Lodges
    Génération automatique après réservation
    """
    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('emise', 'Émise'),
        ('payee', 'Payée'),
        ('annulee', 'Annulée'),
    ]
    
    # Numérotation automatique
    numero = models.CharField(max_length=20, unique=True, editable=False)
    
    # Relations
    reservation = models.OneToOneField(
        'reservations.Reservation',
        on_delete=models.CASCADE,
        related_name='facture'
    )
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE
    )
    
    # Informations facture
    date_emission = models.DateTimeField(auto_now_add=True)
    date_echeance = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='emise')
    
    # Montants
    montant_ht = models.DecimalField(max_digits=10, decimal_places=2)
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('19.25'))  # TVA Cameroun
    montant_tva = models.DecimalField(max_digits=10, decimal_places=2)
    montant_ttc = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Détails supplémentaires
    frais_menage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    frais_service = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remise = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Notes
    notes = models.TextField(blank=True)
    conditions_paiement = models.TextField(default="Paiement à réception de facture")
    
    # Métadonnées
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_emission']
        verbose_name = 'Facture'
        verbose_name_plural = 'Factures'
    
    def __str__(self):
        return f"Facture {self.numero} - {self.client.nom}"
    
    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.generer_numero()
        
        # Calculs automatiques
        self.calculer_montants()
        
        super().save(*args, **kwargs)
    
    def generer_numero(self):
        """Génère un numéro de facture unique"""
        annee = datetime.now().year
        
        # Compter les factures de l'année
        count = Facture.objects.filter(
            date_emission__year=annee
        ).count() + 1
        
        return f"FAC{annee}{count:04d}"
    
    def calculer_montants(self):
        """Calcule les montants HT, TVA et TTC"""
        if self.reservation:
            # Montant de base du séjour
            self.montant_ht = self.reservation.prix_total
            
            # Ajouter les frais
            self.montant_ht += self.frais_menage + self.frais_service
            
            # Appliquer la remise
            self.montant_ht -= self.remise
            
            # Calculer la TVA
            self.montant_tva = self.montant_ht * (self.taux_tva / 100)
            
            # Montant TTC
            self.montant_ttc = self.montant_ht + self.montant_tva
    
    def get_details_sejour(self):
        """Retourne les détails du séjour pour la facture"""
        if not self.reservation:
            return {}
            
        return {
            'appartement': self.reservation.appartement.numero,
            'type_logement': self.reservation.appartement.get_type_logement_display(),
            'date_arrivee': self.reservation.date_arrivee,
            'date_depart': self.reservation.date_depart,
            'nombre_nuits': self.reservation.nombre_nuits,
            'prix_par_nuit': self.reservation.appartement.prix_par_nuit,
            'montant_sejour': self.reservation.prix_total,
        }
    
    def get_lignes_facture(self):
        """Retourne les lignes de facturation détaillées"""
        lignes = []
        
        if self.reservation:
            # Ligne principale du séjour
            lignes.append({
                'designation': f"Séjour - Appartement {self.reservation.appartement.numero}",
                'description': f"Du {self.reservation.date_arrivee.strftime('%d/%m/%Y')} au {self.reservation.date_depart.strftime('%d/%m/%Y')}",
                'quantite': self.reservation.nombre_nuits,
                'unite': 'nuit(s)',
                'prix_unitaire': self.reservation.appartement.prix_par_nuit,
                'montant': self.reservation.prix_total,
            })
            
            # Frais de ménage
            if self.frais_menage > 0:
                lignes.append({
                    'designation': 'Frais de ménage',
                    'description': 'Nettoyage de fin de séjour',
                    'quantite': 1,
                    'unite': 'forfait',
                    'prix_unitaire': self.frais_menage,
                    'montant': self.frais_menage,
                })
            
            # Frais de service
            if self.frais_service > 0:
                lignes.append({
                    'designation': 'Frais de service',
                    'description': 'Frais administratifs',
                    'quantite': 1,
                    'unite': 'forfait',
                    'prix_unitaire': self.frais_service,
                    'montant': self.frais_service,
                })
            
            # Remise
            if self.remise > 0:
                lignes.append({
                    'designation': 'Remise',
                    'description': 'Réduction accordée',
                    'quantite': 1,
                    'unite': 'forfait',
                    'prix_unitaire': -self.remise,
                    'montant': -self.remise,
                })
        
        return lignes


class ParametresFacturation(models.Model):
    """
    Paramètres globaux pour la facturation RepAvi
    """
    # Informations entreprise
    nom_entreprise = models.CharField(max_length=100, default="RepAvi Lodges")
    adresse = models.TextField(default="Yaoundé, Cameroun")
    telephone = models.CharField(max_length=20, default="+237 XXX XXX XXX")
    email = models.EmailField(default="contact@repavilodges.com")
    site_web = models.URLField(blank=True)
    
    # Informations légales
    numero_contribuable = models.CharField(max_length=50, blank=True)
    numero_rccm = models.CharField(max_length=50, blank=True)
    
    # Paramètres de facturation
    taux_tva_defaut = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('19.25'),
        help_text="Taux TVA par défaut (%)"
    )
    frais_menage_defaut = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('5000'),
        help_text="Frais de ménage par défaut (FCFA)"
    )
    
    # Conditions de paiement
    delai_paiement_jours = models.IntegerField(
        default=30,
        help_text="Délai de paiement en jours"
    )
    conditions_generales = models.TextField(
        default="Paiement à réception de facture. Pénalités de retard applicables."
    )
    
    # Mentions légales
    mentions_legales = models.TextField(
        default="RepAvi Lodges - Société de droit camerounais"
    )
    
    class Meta:
        verbose_name = 'Paramètres de facturation'
        verbose_name_plural = 'Paramètres de facturation'
    
    def __str__(self):
        return self.nom_entreprise
    
    @classmethod
    def get_parametres(cls):
        """Récupère les paramètres (singleton)"""
        parametres, created = cls.objects.get_or_create(pk=1)
        return parametres