# ==========================================
# apps/facturation/forms.py - Facturation PDF
# ==========================================
from django import forms
from .models import Facture

class FactureForm(forms.ModelForm):
    """
    Formulaire facture selon cahier des charges
    Génération automatique avec infos complètes
    """
    
    class Meta:
        model = Facture
        fields = ['frais_supplementaires']
        widgets = {
            'frais_supplementaires': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'min': '0',
                'step': '100',
                'placeholder': '0'
            }),
        }
        labels = {
            'frais_supplementaires': 'Frais supplémentaires (FCFA)',
        }
        help_texts = {
            'frais_supplementaires': 'Frais de ménage, caution, etc. (optionnel)',
        }