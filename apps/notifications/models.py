# ==========================================
# apps/notifications/models.py
# ==========================================
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.users.models import User

class Notification(models.Model):
    TYPE_CHOICES = [
        ('reservation', 'Réservation'),
        ('paiement', 'Paiement'),
        ('menage', 'Ménage'),
        ('maintenance', 'Maintenance'),
        ('client', 'Client'),
        ('system', 'Système'),
    ]
    
    ACTION_CHOICES = [
        ('created', 'créé'),
        ('updated', 'modifié'),
        ('assigned', 'affecté'),
        ('completed', 'terminé'),
        ('cancelled', 'annulé'),
        ('overdue', 'en retard'),
    ]
    
    # Destinataire
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications')
    
    # Contenu
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Acteur de l'action
    actor = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Lien
    url = models.URLField(blank=True)
    url_text = models.CharField(max_length=50, default='Voir')
    
    # Métadonnées
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Objet lié (générique)
    object_type = models.CharField(max_length=50, blank=True)  # 'reservation', 'paiement', etc.
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_name = models.CharField(max_length=200, blank=True)  # "Réservation #123", "Apt M001"
    
    def mark_as_read(self):
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save()
    
    def get_icon(self):
        icons = {
            'reservation': 'event',
            'paiement': 'payments',
            'menage': 'cleaning_services',
            'maintenance': 'build',
            'client': 'person',
            'system': 'settings',
        }
        return icons.get(self.type, 'notifications')
    
    def get_color(self):
        colors = {
            'created': 'green',
            'assigned': 'blue', 
            'overdue': 'red',
            'completed': 'green',
            'cancelled': 'gray',
        }
        return colors.get(self.action, 'blue')
    
    class Meta:
        ordering = ['-created_at']

