# ==========================================
# apps/reservations/forms.py - Réservations selon 5 étapes cahier
# ==========================================
from django import forms
from django.core.exceptions import ValidationError
from .models import Reservation
from apps.clients.models import Client
from apps.appartements.models import Appartement

class ReservationForm(forms.ModelForm):
    """
    Formulaire réservation selon cahier des charges
    5 étapes : Client → Appartement → Dates → Tarif → Paiement
    """
    
    class Meta:
        model = Reservation
        fields = ['client', 'appartement', 'date_arrivee', 'date_depart', 'statut']
        widgets = {
            'client': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'appartement': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'onchange': 'calculerPrix()'
            }),
            'date_arrivee': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'onchange': 'calculerPrix()'
            }),
            'date_depart': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'onchange': 'calculerPrix()'
            }),
            'statut': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
        }
        labels = {
            'client': '1. Sélectionner le client',
            'appartement': '2. Choisir l\'appartement',
            'date_arrivee': '3. Date d\'arrivée',
            'date_depart': '3. Date de départ',
            'statut': '4. Statut de la réservation',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les appartements disponibles
        self.fields['appartement'].queryset = Appartement.objects.filter(statut='disponible')
        
        # Ajouter option "Nouveau client"
        self.fields['client'].empty_label = "-- Sélectionner un client ou créer nouveau --"
    
    def clean(self):
        """Validation selon cahier - vérification conflits"""
        cleaned_data = super().clean()
        date_arrivee = cleaned_data.get('date_arrivee')
        date_depart = cleaned_data.get('date_depart')
        appartement = cleaned_data.get('appartement')
        
        if date_arrivee and date_depart and appartement:
            # Vérifier conflits selon cahier
            conflits = Reservation.objects.filter(
                appartement=appartement,
                statut__in=['confirmee', 'en_cours']
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
            
            for conflit in conflits:
                if (date_arrivee < conflit.date_depart and 
                    date_depart > conflit.date_arrivee):
                    raise ValidationError(
                        f'Conflit de dates avec une réservation existante '
                        f'({conflit.date_arrivee} au {conflit.date_depart})'
                    )
        
        return cleaned_data
