# ==========================================
# apps/facturation/models.py - Facturation PDF
# ==========================================
from django.db import models

class Facture(models.Model):
    """
    Facture PDF selon cahier des charges
    """
    # Liens
    reservation = models.OneToOneField('reservations.Reservation', on_delete=models.CASCADE)
    
    # Informations facture (selon cahier)
    numero_facture = models.CharField(max_length=20, unique=True, verbose_name='Numéro')
    date_emission = models.DateField(auto_now_add=True, verbose_name='Date émission')
    
    # Montants
    montant_sejour = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Montant séjour')
    frais_supplementaires = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Frais supplémentaires')
    montant_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Montant total')
    
    # Fichier PDF généré
    fichier_pdf = models.FileField(upload_to='factures/', blank=True)
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    gestionnaire = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    
    def save(self, *args, **kwargs):
        # Générer numéro automatique selon cahier
        if not self.numero_facture:
            from datetime import datetime
            year = datetime.now().year
            last_num = Facture.objects.filter(
                numero_facture__startswith=f'FAC{year}'
            ).count()
            self.numero_facture = f'FAC{year}{str(last_num + 1).zfill(4)}'
        
        # Calculs selon cahier
        self.montant_sejour = self.reservation.prix_total
        self.montant_total = self.montant_sejour + self.frais_supplementaires
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Facture {self.numero_facture} - {self.reservation.client}"
    
    class Meta:
        verbose_name = 'Facture'
        verbose_name_plural = 'Factures'
        ordering = ['-date_creation']