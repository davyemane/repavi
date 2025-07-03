# avis/models.py
from django.db import models
from users.models import *
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count

class Avis(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='avis')
    maison = models.ForeignKey('home.Maison', on_delete=models.CASCADE, related_name='avis')
    note = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Note de 1 à 5 étoiles"
    )
    commentaire = models.TextField(max_length=1000)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
    
    def __str__(self):
        return f"{self.user.username} - {self.maison.nom} ({self.note}★)"
    
    @property
    def nom_utilisateur(self):
        return self.user.username

# Méthodes utilitaires pour la maison
def get_note_moyenne(self):
    """Retourne la note moyenne de la maison"""
    avg = self.avis.aggregate(Avg('note'))['note__avg']
    return round(avg, 1) if avg else 0

def get_nombre_avis(self):
    """Retourne le nombre total d'avis"""
    return self.avis.count()

# Ajouter ces méthodes à votre modèle Maison
# Maison.add_to_class('get_note_moyenne', get_note_moyenne)
# Maison.add_to_class('get_nombre_avis', get_nombre_avis)