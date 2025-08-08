# ==========================================
# apps/paiements/forms.py - Paiements par tranches SIMPLIFIÉ
# ==========================================
from django import forms
from django.core.exceptions import ValidationError
from .models import EcheancierPaiement

class PaiementForm(forms.ModelForm):
    """
    Formulaire paiement simple selon cahier
    Enregistrement manuel des paiements reçus
    """
    
    class Meta:
        model = EcheancierPaiement
        fields = ['montant_paye', 'mode_paiement', 'commentaire']
        widgets = {
            'montant_paye': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'min': '0',
                'step': '100',
                'placeholder': 'Montant reçu en FCFA'
            }),
            'mode_paiement': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'rows': 3,
                'placeholder': 'Notes sur le paiement (optionnel)'
            }),
        }
        labels = {
            'montant_paye': 'Montant reçu (FCFA)',
            'mode_paiement': 'Mode de paiement',
            'commentaire': 'Commentaire',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pré-remplir le montant avec le montant prévu
        if self.instance and self.instance.montant_prevu:
            self.fields['montant_paye'].widget.attrs['value'] = self.instance.montant_prevu


class EcheancierForm(forms.Form):
    """
    Formulaire pour définir un échéancier selon cahier
    Plan simple : Acompte + Solde
    """
    PLAN_CHOICES = [
        ('standard', 'Plan standard (40% + 60%)'),
        ('complet', 'Paiement complet à l\'arrivée'),
        ('personnalise', 'Plan personnalisé'),
    ]
    
    plan_paiement = forms.ChoiceField(
        choices=PLAN_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'space-y-2'}),
        label='Type de plan de paiement'
    )
    
    # Pour plan personnalisé
    pourcentage_acompte = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'w-20 px-3 py-2 border border-gray-300 rounded-lg',
            'placeholder': '40'
        }),
        label='% d\'acompte'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        plan = cleaned_data.get('plan_paiement')
        
        if plan == 'personnalise' and not cleaned_data.get('pourcentage_acompte'):
            raise ValidationError('Pourcentage d\'acompte requis pour plan personnalisé')
        
        return cleaned_data
