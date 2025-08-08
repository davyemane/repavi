# ==========================================
# apps/menage/forms.py - Planning ménage basique
# ==========================================
from django import forms
from .models import TacheMenage

class TacheMenageForm(forms.ModelForm):
    """
    Check-list simple selon cahier des charges
    """
    
    class Meta:
        model = TacheMenage
        fields = [
            'menage_general_fait', 'equipements_verifies', 
            'problemes_signales', 'temps_passe',
            'photo_avant', 'photo_apres', 'notes_personnel'
        ]
        widgets = {
            'menage_general_fait': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
            }),
            'equipements_verifies': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
            }),
            'problemes_signales': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'rows': 3,
                'placeholder': 'Décrire les problèmes rencontrés (si applicable)'
            }),
            'temps_passe': forms.NumberInput(attrs={
                'class': 'w-32 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'min': '0',
                'placeholder': 'Minutes'
            }),
            'photo_avant': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600',
                'accept': 'image/*'
            }),
            'photo_apres': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600',
                'accept': 'image/*'
            }),
            'notes_personnel': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'rows': 3,
                'placeholder': 'Notes du personnel de ménage'
            }),
        }
        labels = {
            'menage_general_fait': 'Ménage général effectué',
            'equipements_verifies': 'Équipements vérifiés',
            'problemes_signales': 'Problèmes signalés',
            'temps_passe': 'Temps passé (minutes)',
            'photo_avant': 'Photo avant ménage (optionnel)',
            'photo_apres': 'Photo après ménage (optionnel)',
            'notes_personnel': 'Notes du personnel',
        }
