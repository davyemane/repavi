# ==========================================
# apps/facturation/models.py
# ==========================================
from django.db import models
from django.conf import settings
from decimal import Decimal
from datetime import datetime, date, timedelta


def get_date_echeance_defaut():
    """Retourne la date d'échéance par défaut (aujourd'hui + 30 jours)"""
    return date.today() + timedelta(days=30)

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
    date_echeance = models.DateField(default=get_date_echeance_defaut)  # ✅ CORRIGÉ : Date + 30 jours
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='emise')
    
    # Montants
    montant_ht = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('19.25'))  # TVA Cameroun
    montant_tva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    montant_ttc = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
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
            'date_arrivee': self.reservation.date_arrivee,
            'date_depart': self.reservation.date_depart,
            'nombre_nuits': self.reservation.nombre_nuits,
            'prix_nuit': self.reservation.appartement.prix_nuit,
        }


class ParametresFacturation(models.Model):
    """
    Paramètres globaux pour la facturation RepAvi
    """
    # Informations entreprise
    nom_entreprise = models.CharField(max_length=200, default="RepAvi Lodges")
    adresse = models.TextField(default="Yaoundé, Cameroun")
    telephone = models.CharField(max_length=50, default="+237 XXX XXX XXX")
    email = models.EmailField(default="contact@repavi.com")
    
    # Paramètres fiscaux
    numero_contribuable = models.CharField(max_length=50, blank=True)
    taux_tva_defaut = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('19.25'))
    
    # Templates
    footer_facture = models.TextField(
        default="Merci de votre confiance. RepAvi Lodges - Votre séjour, notre priorité."
    )
    
    class Meta:
        verbose_name = "Paramètres Facturation"
        verbose_name_plural = "Paramètres Facturation"
    
    def __str__(self):
        return f"Paramètres {self.nom_entreprise}"
    
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