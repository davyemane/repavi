# ==========================================
# apps/comptabilite/forms.py - Comptabilité simple
# ==========================================
from django import forms
from .models import ComptabiliteAppartement

class MouvementComptableForm(forms.ModelForm):
    """
    Formulaire pour ajouter revenus/charges selon cahier
    Pas de calculs complexes - juste addition/soustraction
    """
    
    class Meta:
        model = ComptabiliteAppartement
        fields = ['appartement', 'type_mouvement', 'libelle', 'montant', 'date_mouvement']
        widgets = {
            'appartement': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'type_mouvement': forms.RadioSelect(attrs={
                'class': 'space-y-2'
            }),
            'libelle': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'placeholder': 'Ex: Ménage, Réparation TV, Séjour Client X...'
            }),
            'montant': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'min': '0',
                'step': '100',
                'placeholder': '15000'
            }),
            'date_mouvement': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
        }
        labels = {
            'appartement': 'Appartement concerné',
            'type_mouvement': 'Type de mouvement',
            'libelle': 'Description',
            'montant': 'Montant (FCFA)',
            'date_mouvement': 'Date',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Date du jour par défaut
        from django.utils import timezone
        self.fields['date_mouvement'].initial = timezone.now().date()