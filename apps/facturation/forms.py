# ==========================================
# apps/facturation/forms.py
# ==========================================
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime, timedelta
from .models import Facture, ParametresFacturation


class FactureForm(forms.ModelForm):
    """
    Formulaire pour créer/modifier une facture RepAvi
    """
    
    class Meta:
        model = Facture
        fields = [
            'reservation', 'client', 'date_echeance', 
            'frais_menage', 'frais_service', 'remise',
            'notes', 'conditions_paiement', 'statut'
        ]
        widgets = {
            'reservation': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'client': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'date_echeance': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'frais_menage': forms.NumberInput(attrs={
                'step': '500',
                'min': '0',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato',
                'placeholder': '0'
            }),
            'frais_service': forms.NumberInput(attrs={
                'step': '500',
                'min': '0',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato',
                'placeholder': '0'
            }),
            'remise': forms.NumberInput(attrs={
                'step': '500',
                'min': '0',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato',
                'placeholder': '0'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato',
                'placeholder': 'Notes additionnelles pour cette facture...'
            }),
            'conditions_paiement': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'statut': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            })
        }
        labels = {
            'reservation': 'Réservation',
            'client': 'Client',
            'date_echeance': 'Date d\'échéance',
            'frais_menage': 'Frais de ménage (FCFA)',
            'frais_service': 'Frais de service (FCFA)',
            'remise': 'Remise accordée (FCFA)',
            'notes': 'Notes',
            'conditions_paiement': 'Conditions de paiement',
            'statut': 'Statut de la facture',
        }
        help_texts = {
            'frais_menage': 'Frais de nettoyage de fin de séjour',
            'frais_service': 'Frais administratifs ou services supplémentaires',
            'remise': 'Réduction accordée au client',
            'notes': 'Informations supplémentaires qui apparaîtront sur la facture',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Définir des valeurs par défaut
        if not self.instance.pk:  # Nouvelle facture
            parametres = ParametresFacturation.get_parametres()
            self.fields['frais_menage'].initial = parametres.frais_menage_defaut
            self.fields['conditions_paiement'].initial = parametres.conditions_generales
            self.fields['date_echeance'].initial = datetime.now().date() + timedelta(days=parametres.delai_paiement_jours)
    
    def clean_date_echeance(self):
        """Valide que la date d'échéance n'est pas dans le passé"""
        date_echeance = self.cleaned_data.get('date_echeance')
        if date_echeance and date_echeance < datetime.now().date():
            raise ValidationError("La date d'échéance ne peut pas être dans le passé.")
        return date_echeance
    
    def clean_frais_menage(self):
        """Valide les frais de ménage"""
        frais = self.cleaned_data.get('frais_menage', 0)
        if frais < 0:
            raise ValidationError("Les frais de ménage ne peuvent pas être négatifs.")
        if frais > 50000:  # Limite raisonnable
            raise ValidationError("Les frais de ménage semblent anormalement élevés.")
        return frais
    
    def clean_frais_service(self):
        """Valide les frais de service"""
        frais = self.cleaned_data.get('frais_service', 0)
        if frais < 0:
            raise ValidationError("Les frais de service ne peuvent pas être négatifs.")
        return frais
    
    def clean_remise(self):
        """Valide la remise"""
        remise = self.cleaned_data.get('remise', 0)
        if remise < 0:
            raise ValidationError("La remise ne peut pas être négative.")
        return remise
    
    def clean(self):
        """Validation globale du formulaire"""
        cleaned_data = super().clean()
        reservation = cleaned_data.get('reservation')
        client = cleaned_data.get('client')
        remise = cleaned_data.get('remise', 0)
        
        # Vérifier la cohérence réservation/client
        if reservation and client and reservation.client != client:
            raise ValidationError("Le client sélectionné ne correspond pas à la réservation.")
        
        # Vérifier que la remise n'est pas supérieure au montant total
        if reservation and remise:
            montant_base = reservation.prix_total
            frais_menage = cleaned_data.get('frais_menage', 0)
            frais_service = cleaned_data.get('frais_service', 0)
            montant_total = montant_base + frais_menage + frais_service
            
            if remise > montant_total:
                raise ValidationError(
                    f"La remise ({remise:,.0f} FCFA) ne peut pas être supérieure "
                    f"au montant total ({montant_total:,.0f} FCFA)."
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """Sauvegarde avec utilisateur créateur"""
        facture = super().save(commit=False)
        
        if not facture.pk and self.user:  # Nouvelle facture
            facture.cree_par = self.user
        
        if commit:
            facture.save()
        
        return facture


class GenerationFactureForm(forms.Form):
    """
    Formulaire simplifié pour générer une facture depuis une réservation
    """
    
    frais_menage = forms.DecimalField(
        label='Frais de ménage (FCFA)',
        initial=5000,
        min_value=0,
        max_value=50000,
        widget=forms.NumberInput(attrs={
            'step': '500',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
        }),
        help_text='Frais de nettoyage de fin de séjour'
    )
    
    frais_service = forms.DecimalField(
        label='Frais de service (FCFA)',
        initial=0,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'step': '500',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
        }),
        help_text='Frais administratifs (optionnel)'
    )
    
    remise = forms.DecimalField(
        label='Remise accordée (FCFA)',
        initial=0,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'step': '500',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
        }),
        help_text='Réduction accordée au client (optionnel)'
    )
    
    notes = forms.CharField(
        label='Notes',
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato',
            'placeholder': 'Notes additionnelles pour cette facture...'
        }),
        help_text='Ces notes apparaîtront sur la facture PDF'
    )
    
    def __init__(self, *args, **kwargs):
        self.reservation = kwargs.pop('reservation', None)
        super().__init__(*args, **kwargs)
        
        # Valeurs par défaut selon les paramètres
        parametres = ParametresFacturation.get_parametres()
        self.fields['frais_menage'].initial = parametres.frais_menage_defaut
    
    def clean_remise(self):
        """Valide que la remise n'est pas supérieure au montant total"""
        remise = self.cleaned_data.get('remise', 0)
        
        if self.reservation and remise:
            frais_menage = self.cleaned_data.get('frais_menage', 0)
            frais_service = self.cleaned_data.get('frais_service', 0)
            montant_total = self.reservation.prix_total + frais_menage + frais_service
            
            if remise > montant_total:
                raise ValidationError(
                    f"La remise ne peut pas être supérieure au montant total "
                    f"({montant_total:,.0f} FCFA)."
                )
        
        return remise


class ParametresFacturationForm(forms.ModelForm):
    """
    Formulaire pour configurer les paramètres de facturation RepAvi
    """
    
    class Meta:
        model = ParametresFacturation
        fields = '__all__'
        widgets = {
            'nom_entreprise': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'adresse': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato',
                'placeholder': '+237 XXX XXX XXX'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'site_web': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato',
                'placeholder': 'https://www.repavilodges.com'
            }),
            'numero_contribuable': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'numero_rccm': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'taux_tva_defaut': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'max': '50',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'frais_menage_defaut': forms.NumberInput(attrs={
                'step': '500',
                'min': '0',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'delai_paiement_jours': forms.NumberInput(attrs={
                'min': '1',
                'max': '365',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'conditions_generales': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
            'mentions_legales': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
            }),
        }
    
    def clean_taux_tva_defaut(self):
        """Valide le taux de TVA"""
        taux = self.cleaned_data.get('taux_tva_defaut')
        if taux < 0 or taux > 50:
            raise ValidationError("Le taux de TVA doit être entre 0% et 50%.")
        return taux
    
    def clean_email(self):
        """Valide l'email de l'entreprise"""
        email = self.cleaned_data.get('email')
        if email and not email.endswith(('.com', '.fr', '.org', '.net', '.cm')):
            raise ValidationError("Veuillez utiliser une adresse email valide.")
        return email


class RechercheFactureForm(forms.Form):
    """
    Formulaire de recherche et filtrage des factures
    """
    
    recherche = forms.CharField(
        label='Recherche',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato',
            'placeholder': 'Numéro facture, nom client, email...'
        })
    )
    
    statut = forms.ChoiceField(
        label='Statut',
        required=False,
        choices=[('', 'Tous les statuts')] + Facture.STATUT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
        })
    )
    
    date_debut = forms.DateField(
        label='Date de début',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
        })
    )
    
    date_fin = forms.DateField(
        label='Date de fin',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
        })
    )
    
    montant_min = forms.DecimalField(
        label='Montant minimum (FCFA)',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'step': '1000',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
        })
    )
    
    montant_max = forms.DecimalField(
        label='Montant maximum (FCFA)',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'step': '1000',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#02066F] focus:ring-2 focus:ring-blue-100 font-lato'
        })
    )
    
    def clean(self):
        """Validation croisée des champs"""
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        montant_min = cleaned_data.get('montant_min')
        montant_max = cleaned_data.get('montant_max')
        
        # Vérifier les dates
        if date_debut and date_fin and date_debut > date_fin:
            raise ValidationError("La date de début doit être antérieure à la date de fin.")
        
        # Vérifier les montants
        if montant_min and montant_max and montant_min > montant_max:
            raise ValidationError("Le montant minimum doit être inférieur au montant maximum.")
        
        return cleaned_data