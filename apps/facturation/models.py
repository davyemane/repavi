# ==========================================
# apps/facturation/models.py - CORRIGÉ
# ==========================================
from django.db import models
from django.conf import settings
from decimal import Decimal
from datetime import datetime, date, timedelta


def get_date_echeance_defaut():
    """Retourne la date d'échéance par défaut (aujourd'hui + 30 jours)"""
    return date.today() + timedelta(days=30)


class ParametresFacturation(models.Model):
    """Paramètres globaux de facturation"""
    # Informations entreprise
    nom_entreprise = models.CharField(max_length=200, default="RepAvi Lodges")
    adresse = models.TextField(default="Yaoundé, Cameroun")
    telephone = models.CharField(max_length=50, default="+237 XXX XXX XXX")
    email = models.EmailField(default="contact@repavi.com")
    
    # Paramètres
    delai_paiement_jours = models.IntegerField(default=30)
    frais_menage_defaut = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taux_tva_defaut = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('19.25'))
    
    # Templates
    footer_facture = models.TextField(
        default="Merci de votre confiance. RepAvi Lodges - Votre séjour, notre priorité."
    )
    
    @classmethod
    def get_parametres(cls):
        """Récupère ou crée les paramètres par défaut"""
        parametres, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'nom_entreprise': 'RepAvi Lodges',
                'adresse': 'Yaoundé, Cameroun',
                'telephone': '+237 XXX XXX XXX',
                'email': 'contact@repavi.com',
            }
        )
        return parametres
    
    def save(self, *args, **kwargs):
        """Assurer qu'il n'y a qu'une seule instance"""
        self.pk = 1
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Paramètres Facturation"
        verbose_name_plural = "Paramètres Facturation"
    
    def __str__(self):
        return f"Paramètres {self.nom_entreprise}"


class Facture(models.Model):
    """
    Facture par paiement/tranche - UNE facture par paiement effectué
    """
    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('emise', 'Émise'),
        ('payee', 'Payée'),
        ('annulee', 'Annulée'),
    ]
    
    TYPE_FACTURE_CHOICES = [
        ('acompte', 'Facture d\'acompte'),
        ('solde', 'Facture de solde'),
        ('complete', 'Facture complète'),
    ]
    
    # Numérotation automatique
    numero = models.CharField(max_length=20, unique=True, editable=False)
    
    # Relations - UNE facture par paiement
    echeance_paiement = models.OneToOneField(
        'paiements.EcheancierPaiement',
        on_delete=models.CASCADE,
        related_name='facture',
        help_text="Paiement associé à cette facture"
    )
    
    # Relations dérivées (pour faciliter les requêtes)
    reservation = models.ForeignKey(
        'reservations.Reservation',
        on_delete=models.CASCADE,
        related_name='factures'
    )
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE
    )
    
    # Type de facture
    type_facture = models.CharField(
        max_length=20, 
        choices=TYPE_FACTURE_CHOICES,
        help_text="Type de facture selon le paiement"
    )
    
    # Informations facture
    date_emission = models.DateTimeField(auto_now_add=True)
    date_echeance = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='payee')
    
    # Montants (calculés depuis le paiement)
    montant_paiement = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Montant de CE paiement spécifique"
    )
    montant_ht = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('19.25'))
    montant_tva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    montant_ttc = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Informations contexte (au moment du paiement)
    solde_avant_paiement = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Solde restant avant ce paiement"
    )
    solde_apres_paiement = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Solde restant après ce paiement"
    )
    
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
    
    class Meta:
        ordering = ['-date_emission']
        verbose_name = 'Facture'
        verbose_name_plural = 'Factures'
    
    def __str__(self):
        return f"Facture {self.numero} - {self.get_type_facture_display()} - {self.montant_ttc} FCFA"
    
    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.generer_numero()
        
        # Auto-remplir depuis l'échéance
        if self.echeance_paiement:
            self.reservation = self.echeance_paiement.reservation
            self.client = self.echeance_paiement.reservation.client
            self.type_facture = self.echeance_paiement.type_paiement
            self.montant_paiement = self.echeance_paiement.montant_paye
        
        # Calculs automatiques
        self.calculer_montants()
        
        super().save(*args, **kwargs)
    
    def generer_numero(self):
        """Génère un numéro de facture unique"""
        annee = datetime.now().year
        mois = datetime.now().month
        
        # Compter les factures du mois
        count = Facture.objects.filter(
            date_emission__year=annee,
            date_emission__month=mois
        ).count() + 1
        
        # Format : FAC2024010001 (année + mois + numéro)
        return f"FAC{annee}{mois:02d}{count:04d}"
    
    def calculer_montants(self):
        """Calcule les montants de cette facture"""
        # Montant HT = montant du paiement
        self.montant_ht = self.montant_paiement
        
        # Calculer la TVA
        self.montant_tva = self.montant_ht * (self.taux_tva / 100)
        
        # Montant TTC
        self.montant_ttc = self.montant_ht + self.montant_tva
    
    def calculer_contexte_paiement(self):
        """Calcule le contexte du paiement (soldes avant/après)"""
        from django.db.models import Sum
        
        # Total déjà payé AVANT ce paiement
        paiements_precedents = self.reservation.echeanciers.filter(
            statut='paye',
            date_paiement__lt=self.echeance_paiement.date_paiement
        ).aggregate(total=Sum('montant_paye'))
        
        total_precedent = paiements_precedents.get('total') or Decimal('0')
        
        # Solde avant = Total réservation - Paiements précédents
        self.solde_avant_paiement = self.reservation.prix_total - total_precedent
        
        # Solde après = Solde avant - Ce paiement
        self.solde_apres_paiement = self.solde_avant_paiement - self.montant_paiement
    
    def get_details_sejour(self):
        """Retourne les détails du séjour"""
        if not self.reservation:
            return {}
            
        return {
            'appartement': self.reservation.appartement.numero,
            'date_arrivee': self.reservation.date_arrivee,
            'date_depart': self.reservation.date_depart,
            'nombre_nuits': self.reservation.nombre_nuits,
            'prix_nuit': self.reservation.appartement.prix_par_nuit,
        }
    
    def get_lignes_facture(self):
        """Retourne les lignes de cette facture de paiement"""
        lignes = []
        
        # Ligne principale : ce paiement
        lignes.append({
            'description': f'{self.get_type_facture_display()} - Séjour {self.reservation.appartement.numero}',
            'detail': f'Paiement du {self.echeance_paiement.date_paiement.strftime("%d/%m/%Y")}',
            'quantite': 1,
            'prix_unitaire': self.montant_paiement,
            'total': self.montant_paiement
        })
        
        return lignes
    
    def get_autres_paiements(self):
        """Récupère les autres paiements de cette réservation"""
        return self.reservation.echeanciers.filter(
            statut='paye'
        ).exclude(pk=self.echeance_paiement.pk).order_by('date_paiement')
    
    @property
    def est_paiement_final(self):
        """Vérifie si c'est le dernier paiement de la réservation"""
        return self.solde_apres_paiement <= 0