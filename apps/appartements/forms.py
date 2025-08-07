# apps/appartements/forms.py - Formulaires appartements
from django import forms
from django.core.exceptions import ValidationError
from .models import Appartement, PhotoAppartement

class AppartementForm(forms.ModelForm):
    """
    Formulaire appartement selon cahier des charges
    Créer en moins de 2 minutes
    """
    
    # Équipements prédéfinis selon cahier (liste simple)
    EQUIPEMENTS_PREDEFINED = [
        'TV', 'Frigo', 'Climatisation', 'Micro-ondes', 'Bouilloire',
        'Canapé', 'Table basse', 'Lit double', 'Armoire', 'Chaises',
        'Wifi', 'Balcon', 'Parking', 'Sécurité 24h', 'Générateur'
    ]
    
    equipements_choix = forms.MultipleChoiceField(
        choices=[(eq, eq) for eq in EQUIPEMENTS_PREDEFINED],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'grid grid-cols-2 gap-2'
        }),
        required=False,
        label='Équipements disponibles'
    )
    
    class Meta:
        model = Appartement
        fields = ['numero', 'type_logement', 'maison', 'prix_par_nuit', 'statut']
        widgets = {
            'numero': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'placeholder': 'Ex: A01, B12, Studio1...'
            }),
            'type_logement': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'maison': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'placeholder': 'Ex: Villa Sunrise, Résidence Palm...'
            }),
            'prix_par_nuit': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'placeholder': '25000',
                'min': '0',
                'step': '1000'
            }),
            'statut': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
        }
        labels = {
            'numero': 'Numéro de l\'appartement',
            'type_logement': 'Type de logement',
            'maison': 'Nom de la maison',
            'prix_par_nuit': 'Prix par nuit (FCFA)',
            'statut': 'Statut actuel',
        }
        help_texts = {
            'numero': 'Identifiant unique (ex: A01, B12)',
            'prix_par_nuit': 'Prix unique et simple par nuit',
        }
    
    def save(self, commit=True):
        """Sauvegarder avec équipements sélectionnés"""
        appartement = super().save(commit=False)
        appartement.equipements = self.cleaned_data.get('equipements_choix', [])
        if commit:
            appartement.save()
        return appartement


class PhotoAppartementForm(forms.ModelForm):
    """Formulaire ajout photos par pièce selon cahier"""
    
    class Meta:
        model = PhotoAppartement
        fields = ['nom_piece', 'photo', 'est_principale', 'ordre']
        widgets = {
            'nom_piece': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'placeholder': 'Salon, Chambre, Cuisine...'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600',
                'accept': 'image/*'
            }),
            'ordre': forms.NumberInput(attrs={
                'class': 'w-20 px-3 py-2 border border-gray-300 rounded-lg',
                'min': '0'
            }),
        }

