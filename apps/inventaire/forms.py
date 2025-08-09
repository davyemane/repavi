# ==========================================
# apps/inventaire/forms.py - Inventaire simplifié
# ==========================================
from django import forms
from .models import EquipementAppartement

class EquipementForm(forms.ModelForm):
    """
    Formulaire équipement selon cahier
    Informations basiques : Prix d'achat, photo
    """
    
    class Meta:
        model = EquipementAppartement
        fields = ['nom', 'etat', 'prix_achat', 'date_achat', 'photo', 'commentaire']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'placeholder': 'Ex: TV Samsung 32", Frigo LG...'
            }),
            'etat': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'prix_achat': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'min': '0',
                'step': '1000',
                'placeholder': '180000'
            }),
            'date_achat': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600',
                'accept': 'image/*'
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'rows': 3,
                'placeholder': 'Notes sur l\'équipement (optionnel)'
            }),
        }
        labels = {
            'nom': 'Nom de l\'équipement',
            'etat': 'État actuel',
            'prix_achat': 'Prix d\'achat (FCFA)',
            'date_achat': 'Date d\'achat',
            'photo': 'Photo de l\'équipement',
            'commentaire': 'Notes et commentaires',
        }


class ChangementEtatForm(forms.Form):
    """
    Formulaire pour changer l'état d'un équipement selon cahier
    Changement d'état en 1 clic avec commentaire
    """
    nouvel_etat = forms.ChoiceField(
        choices=EquipementAppartement.ETAT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'space-y-2'}),
        label='Nouvel état'
    )
    
    commentaire = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
            'rows': 3,
            'placeholder': 'Raison du changement d\'état (optionnel)'
        }),
        label='Commentaire'
    )