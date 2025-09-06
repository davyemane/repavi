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
    
    def clean_montant_paye(self):
        """Validation du montant payé"""
        montant = self.cleaned_data.get('montant_paye')
        
        if montant is None:
            raise ValidationError("Le montant est requis.")
        
        if montant < 0:
            raise ValidationError("Le montant ne peut pas être négatif.")
        
        # Autoriser les montants supérieurs (sur-paiement)
        # if montant > self.instance.montant_prevu:
        #     raise ValidationError(f"Le montant ne peut pas dépasser {self.instance.montant_prevu} FCFA.")
        
        return montant


class EcheancierForm(forms.Form):
    """
    Formulaire pour définir un échéancier selon cahier
    Plan simple : Acompte + Solde
    """
    PLAN_CHOICES = [
        ('40_60', 'Standard : 40% acompte + 60% solde'),
        ('50_50', 'Équilibré : 50% acompte + 50% solde'),
        ('30_70', 'Faible acompte : 30% acompte + 70% solde'),
        ('100_0', 'Paiement intégral immédiat'),
    ]
    
    plan_paiement = forms.ChoiceField(
        choices=PLAN_CHOICES,
        initial='40_60',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
        }),
        label='Plan de paiement'
    )
    
    date_acompte = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
        }),
        label='Date échéance acompte'
    )
    
    date_solde = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
        }),
        label='Date échéance solde'
    )
    
    def clean(self):
        """Validation du formulaire"""
        cleaned_data = super().clean()
        date_acompte = cleaned_data.get('date_acompte')
        date_solde = cleaned_data.get('date_solde')
        
        if date_acompte and date_solde:
            if date_acompte >= date_solde:
                raise ValidationError("La date de l'acompte doit être antérieure à celle du solde.")
        
        return cleaned_data
    
    def get_pourcentages(self):
        """Retourne les pourcentages selon le plan choisi"""
        plan = self.cleaned_data.get('plan_paiement', '40_60')
        
        plans = {
            '40_60': (40, 60),
            '50_50': (50, 50),
            '30_70': (30, 70),
            '100_0': (100, 0),
        }
        
        return plans.get(plan, (40, 60))


class FiltreEcheancierForm(forms.Form):
    """Formulaire de filtrage de l'échéancier"""
    STATUT_CHOICES = [
        ('tous', 'Tous les paiements'),
        ('en_attente', 'En attente'),
        ('paye', 'Payés'),
        ('retard', 'En retard'),
    ]
    
    statut = forms.ChoiceField(
        choices=STATUT_CHOICES,
        required=False,
        initial='tous',
        widget=forms.Select(attrs={
            'class': 'px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-600',
            'onchange': 'this.form.submit()'
        })
    )
    
    appartement = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Tous les appartements",
        widget=forms.Select(attrs={
            'class': 'px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-600',
            'onchange': 'this.form.submit()'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Filtrer les appartements selon l'utilisateur
            from apps.appartements.models import Appartement
            if hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
                self.fields['appartement'].queryset = Appartement.objects.filter(gestionnaire=user)
            else:
                self.fields['appartement'].queryset = Appartement.objects.all()