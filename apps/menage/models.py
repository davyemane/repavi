# ==========================================
# apps/menage/models.py - Planning ménage basique
# ==========================================
from django.db import models


class TypeTache(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    obligatoire = models.BooleanField(default=False)
    ordre = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['ordre', 'nom']
class TacheMenage(models.Model):
    """
    Planning ménage basique selon cahier
    """
    STATUT_CHOICES = [
        ('a_faire', 'À faire'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
    ]
    
    # Liens
    appartement = models.ForeignKey('appartements.Appartement', on_delete=models.CASCADE)
    reservation = models.ForeignKey('reservations.Reservation', on_delete=models.CASCADE, null=True, blank=True)
    
    # Informations tâche
    date_prevue = models.DateField(verbose_name='Date prévue')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='a_faire')
    
    # Check-list simple (selon cahier)
    menage_general_fait = models.BooleanField(default=False, verbose_name='Ménage général fait')
    equipements_verifies = models.BooleanField(default=False, verbose_name='Équipements vérifiés')
    problemes_signales = models.TextField(blank=True, verbose_name='Problèmes signalés')
    temps_passe = models.PositiveIntegerField(null=True, blank=True, verbose_name='Temps passé (minutes)')
    taches_a_effectuer = models.ManyToManyField(TypeTache, blank=True)

    # Photos avant/après (optionnel selon cahier)
    photo_avant = models.ImageField(upload_to='menage/avant/', blank=True)
    photo_apres = models.ImageField(upload_to='menage/apres/', blank=True)
    
    # Personnel
    personnel = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    notes_personnel = models.TextField(blank=True, verbose_name='Notes du personnel')
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_completion = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Ménage {self.appartement.numero} - {self.date_prevue}"
    
    class Meta:
        verbose_name = 'Tâche Ménage'
        verbose_name_plural = 'Tâches Ménage'
        ordering = ['date_prevue', 'appartement__numero']
