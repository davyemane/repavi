from django.db import models


class TacheMenage(models.Model):
    """
    Tâche de ménage simplifiée - auto-générée tous les 2 jours ou après départ
    """
    STATUT_CHOICES = [
        ('a_faire', 'À faire'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
    ]
    
    # Liens
    appartement = models.ForeignKey(
        'appartements.Appartement', 
        on_delete=models.CASCADE,
        related_name='taches_menage'
    )
    reservation = models.ForeignKey(
        'reservations.Reservation', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Réservation qui a déclenché cette tâche (si applicable)"
    )
    
    # Informations tâche
    date_prevue = models.DateField(verbose_name='Date prévue')
    statut = models.CharField(
        max_length=20, 
        choices=STATUT_CHOICES, 
        default='a_faire'
    )
    
    # Rapport obligatoire pour terminer
    rapport = models.TextField(
        blank=True,
        verbose_name='Rapport de ménage',
        help_text='État de la maison, meubles, problèmes constatés, etc.'
    )
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_completion = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Ménage {self.appartement.numero} - {self.date_prevue}"
    
    class Meta:
        verbose_name = 'Tâche Ménage'
        verbose_name_plural = 'Tâches Ménage'
        ordering = ['date_prevue', 'appartement__numero']
        unique_together = ['appartement', 'date_prevue']