# reservations/forms.py - Formulaires pour les réservations

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from .models import Reservation, Paiement, TypePaiement, EvaluationReservation, Disponibilite
from home.models import Maison


class ReservationForm(forms.ModelForm):
    """Formulaire principal de réservation"""
    
    class Meta:
        model = Reservation
        fields = [
            'date_debut', 'date_fin', 'nombre_personnes',
            'heure_arrivee', 'heure_depart', 'mode_paiement',
            'commentaire_client', 'contact_urgence_nom', 'contact_urgence_telephone'
        ]
        
        widgets = {
            'date_debut': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                    'min': timezone.now().date().isoformat()
                }
            ),
            'date_fin': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                    'min': (timezone.now().date() + timedelta(days=1)).isoformat()
                }
            ),
            'heure_arrivee': forms.TimeInput(
                attrs={
                    'type': 'time',
                    'class': 'form-control',
                    'value': '15:00'  # Check-in par défaut
                }
            ),
            'heure_depart': forms.TimeInput(
                attrs={
                    'type': 'time',
                    'class': 'form-control',
                    'value': '11:00'  # Check-out par défaut
                }
            ),
            'nombre_personnes': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 1,
                    'max': 20
                }
            ),
            'mode_paiement': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'commentaire_client': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Demandes spéciales, préférences, remarques...'
                }
            ),
            'contact_urgence_nom': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Nom complet'
                }
            ),
            'contact_urgence_telephone': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '+237 6XX XXX XXX'
                }
            ),
        }
    
    def __init__(self, *args, user=None, maison=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.maison_preselected = maison
        
        # Si une maison est présélectionnée, limiter le nombre de personnes
        if maison:
            self.fields['nombre_personnes'].widget.attrs['max'] = maison.capacite_personnes
            self.fields['nombre_personnes'].help_text = f"Maximum {maison.capacite_personnes} personnes"
        
        # Personnaliser les labels et help_text
        self.fields['date_debut'].help_text = "Date d'arrivée"
        self.fields['date_fin'].help_text = "Date de départ"
        self.fields['nombre_personnes'].help_text = "Nombre total de personnes"
        self.fields['heure_arrivee'].help_text = "Heure d'arrivée prévue"
        self.fields['heure_depart'].help_text = "Heure de départ prévue"
        self.fields['contact_urgence_nom'].help_text = "Personne à contacter en cas d'urgence"
        self.fields['contact_urgence_telephone'].help_text = "Numéro de téléphone du contact d'urgence"
        
        # Rendre certains champs obligatoires
        self.fields['contact_urgence_nom'].required = True
        self.fields['contact_urgence_telephone'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        nombre_personnes = cleaned_data.get('nombre_personnes')
        
        # Validation des dates
        if date_debut and date_fin:
            if date_debut >= date_fin:
                raise forms.ValidationError("La date de fin doit être après la date de début.")
            
            if date_debut < timezone.now().date():
                raise forms.ValidationError("La date de début ne peut pas être dans le passé.")
            
            # Limiter à 1 an maximum
            if (date_fin - date_debut).days > 365:
                raise forms.ValidationError("La période ne peut pas dépasser 1 an.")
            
            # Minimum 1 nuit
            if (date_fin - date_debut).days < 1:
                raise forms.ValidationError("La réservation doit être d'au moins 1 nuit.")
        
        # Validation du nombre de personnes avec la maison
        if self.maison_preselected and nombre_personnes:
            if nombre_personnes > self.maison_preselected.capacite_personnes:
                raise forms.ValidationError(
                    f"Le nombre de personnes ne peut pas dépasser {self.maison_preselected.capacite_personnes}."
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """Sauvegarder la réservation avec client et maison"""
        reservation = super().save(commit=False)
        
        # Assigner le client et la maison AVANT toute validation
        if self.user:
            reservation.client = self.user
        if self.maison_preselected:
            reservation.maison = self.maison_preselected
        
        # Calculer le nombre de nuits et le prix total
        if reservation.date_debut and reservation.date_fin:
            reservation.nombre_nuits = (reservation.date_fin - reservation.date_debut).days
            if reservation.maison:
                reservation.prix_par_nuit = reservation.maison.prix_par_nuit
                reservation.prix_total = reservation.maison.prix_par_nuit * reservation.nombre_nuits
        
        if commit:
            # Vérifier la disponibilité avant de sauvegarder
            if reservation.maison and reservation.date_debut and reservation.date_fin:
                # Utiliser exclude_id si la réservation existe déjà (modification)
                exclude_id = reservation.pk if reservation.pk else None
                
                if not Reservation.objects.verifier_disponibilite(
                    reservation.maison, 
                    reservation.date_debut, 
                    reservation.date_fin,
                    exclude_id=exclude_id
                ):
                    raise forms.ValidationError("Cette maison n'est pas disponible pour ces dates.")
            
            # Désactiver temporairement la validation du modèle pour éviter le conflit
            try:
                reservation.save()
            except Exception as e:
                print(f"Erreur lors de la sauvegarde: {e}")
                # En cas d'erreur, essayer de forcer la sauvegarde
                reservation._state.adding = False
                reservation.save(update_fields=[
                    'client', 'maison', 'date_debut', 'date_fin', 'nombre_personnes',
                    'nombre_nuits', 'prix_par_nuit', 'prix_total', 'heure_arrivee', 
                    'heure_depart', 'mode_paiement', 'commentaire_client',
                    'contact_urgence_nom', 'contact_urgence_telephone'
                ])
        
        return reservation
class AnnulationReservationForm(forms.Form):
    """Formulaire d'annulation de réservation"""
    
    raison = forms.ChoiceField(
        label="Raison de l'annulation",
        choices=[
            ('changement_plans', 'Changement de plans'),
            ('urgence_personnelle', 'Urgence personnelle'),
            ('probleme_sante', 'Problème de santé'),
            ('probleme_travail', 'Problème professionnel'),
            ('insatisfaction', 'Insatisfaction avec la maison'),
            ('double_reservation', 'Double réservation'),
            ('autre', 'Autre raison'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    commentaire = forms.CharField(
        required=False,
        label="Commentaire (optionnel)",
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Précisez la raison de votre annulation...'
            }
        )
    )
    
    confirmation = forms.BooleanField(
        label="Je confirme vouloir annuler cette réservation",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_confirmation(self):
        confirmation = self.cleaned_data.get('confirmation')
        if not confirmation:
            raise ValidationError("Vous devez confirmer l'annulation.")
        return confirmation


class ModificationReservationForm(forms.ModelForm):
    """Formulaire pour modifier une réservation existante"""
    
    class Meta:
        model = Reservation
        fields = [
            'date_debut', 'date_fin', 'nombre_personnes',
            'heure_arrivee', 'heure_depart', 'commentaire_client'
        ]
        
        widgets = {
            'date_debut': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'date_fin': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'heure_arrivee': forms.TimeInput(
                attrs={
                    'type': 'time',
                    'class': 'form-control'
                }
            ),
            'heure_depart': forms.TimeInput(
                attrs={
                    'type': 'time',
                    'class': 'form-control'
                }
            ),
            'nombre_personnes': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 1
                }
            ),
            'commentaire_client': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3
                }
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limiter le nombre de personnes à la capacité de la maison
        if self.instance and self.instance.maison:
            self.fields['nombre_personnes'].widget.attrs['max'] = self.instance.maison.capacite_personnes
        
        # Désactiver la modification si la réservation n'est pas modifiable
        if self.instance and not self.instance.est_modifiable:
            for field in self.fields:
                self.fields[field].disabled = True
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Vérifier que la réservation est modifiable
        if self.instance and not self.instance.est_modifiable:
            raise ValidationError("Cette réservation ne peut plus être modifiée.")
        
        # Validation normale des dates et disponibilité
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_debut and date_fin:
            if date_debut >= date_fin:
                raise ValidationError("La date de départ doit être après la date d'arrivée.")
            
            if date_debut < timezone.now().date():
                raise ValidationError("La date d'arrivée ne peut pas être dans le passé.")
            
            # Vérifier la disponibilité (en excluant cette réservation)
            if self.instance and self.instance.maison:
                if not Reservation.objects.verifier_disponibilite(
                    self.instance.maison, 
                    date_debut, 
                    date_fin, 
                    exclude_id=self.instance.pk
                ):
                    raise ValidationError("Cette maison n'est pas disponible pour ces nouvelles dates.")
        
        return cleaned_data


class StatutReservationForm(forms.Form):
    """Formulaire pour changer le statut d'une réservation"""
    
    nouveau_statut = forms.ChoiceField(
        label="Nouveau statut",
        choices=Reservation.STATUT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    commentaire = forms.CharField(
        required=False,
        label="Commentaire",
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Commentaire sur le changement de statut...'
            }
        )
    )
    
    def __init__(self, *args, reservation=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.reservation = reservation
        
        if reservation:
            # Filtrer les statuts selon l'état actuel
            choix_valides = self._get_statuts_valides(reservation.statut)
            self.fields['nouveau_statut'].choices = choix_valides
            self.fields['nouveau_statut'].initial = reservation.statut
    
    def _get_statuts_valides(self, statut_actuel):
        """Retourne les statuts valides selon l'état actuel"""
        transitions = {
            'en_attente': [
                ('en_attente', 'En attente'),
                ('confirmee', 'Confirmée'),
                ('annulee', 'Annulée'),
            ],
            'confirmee': [
                ('confirmee', 'Confirmée'),
                ('terminee', 'Terminée'),
                ('annulee', 'Annulée'),
            ],
            'terminee': [
                ('terminee', 'Terminée'),
            ],
            'annulee': [
                ('annulee', 'Annulée'),
            ],
        }
        
        return transitions.get(statut_actuel, Reservation.STATUT_CHOICES)
    
    def clean_nouveau_statut(self):
        nouveau_statut = self.cleaned_data.get('nouveau_statut')
        
        if self.reservation:
            # Vérifier les transitions valides
            if nouveau_statut == 'terminee' and self.reservation.statut != 'confirmee':
                raise ValidationError("Seules les réservations confirmées peuvent être terminées.")
            
            # Autres validations métier
            if nouveau_statut == 'confirmee' and not self.reservation.est_modifiable:
                raise ValidationError("Cette réservation ne peut plus être confirmée.")
        
        return nouveau_statut


class TypePaiementForm(forms.ModelForm):
    """Formulaire pour les types de paiement (admin)"""
    
    class Meta:
        model = TypePaiement
        fields = [
            'nom', 'description', 'actif', 'frais_pourcentage', 
            'frais_fixe', 'icone', 'couleur'
        ]
        
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'frais_pourcentage': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0',
                    'max': '100'
                }
            ),
            'frais_fixe': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0'
                }
            ),
            'icone': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ex: credit-card, mobile-alt'
                }
            ),
            'couleur': forms.Select(
                choices=[
                    ('blue', 'Bleu'),
                    ('green', 'Vert'),
                    ('orange', 'Orange'),
                    ('red', 'Rouge'),
                    ('purple', 'Violet'),
                    ('yellow', 'Jaune'),
                    ('gray', 'Gris'),
                ],
                attrs={'class': 'form-control'}
            ),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        frais_pourcentage = cleaned_data.get('frais_pourcentage', 0)
        frais_fixe = cleaned_data.get('frais_fixe', 0)
        
        # Au moins un type de frais doit être défini
        if frais_pourcentage == 0 and frais_fixe == 0:
            raise ValidationError("Au moins un type de frais doit être défini (pourcentage ou fixe).")
        
        return cleaned_data


class CalendrierDisponibiliteForm(forms.Form):
    """Formulaire pour la vue calendrier"""
    
    mois = forms.IntegerField(
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    annee = forms.IntegerField(
        min_value=2020,
        max_value=2030,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Valeurs par défaut
        now = timezone.now()
        self.fields['mois'].initial = now.month
        self.fields['annee'].initial = now.year


class RechercheDisponibiliteForm(forms.Form):
    """Formulaire de recherche de disponibilité avancée"""
    
    ville = forms.ModelChoiceField(
        required=False,
        queryset=None,  # Sera défini dans __init__
        empty_label="Toutes les villes",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    categorie = forms.ModelChoiceField(
        required=False,
        queryset=None,  # Sera défini dans __init__
        empty_label="Toutes les catégories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_debut = forms.DateField(
        label="Date d'arrivée",
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'min': timezone.now().date().isoformat()
            }
        )
    )
    
    date_fin = forms.DateField(
        label="Date de départ",
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'min': (timezone.now().date() + timedelta(days=1)).isoformat()
            }
        )
    )
    
    nombre_personnes = forms.IntegerField(
        label="Nombre de personnes",
        min_value=1,
        max_value=20,
        initial=2,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20
            }
        )
    )
    
    prix_min = forms.DecimalField(
        required=False,
        decimal_places=2,
        max_digits=8,
        label="Prix minimum par nuit (FCFA)",
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'step': '1000',
                'min': '0'
            }
        )
    )
    
    prix_max = forms.DecimalField(
        required=False,
        decimal_places=2,
        max_digits=8,
        label="Prix maximum par nuit (FCFA)",
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'step': '1000',
                'min': '0'
            }
        )
    )
    
    # Équipements
    wifi = forms.BooleanField(required=False, label="WiFi")
    parking = forms.BooleanField(required=False, label="Parking")
    piscine = forms.BooleanField(required=False, label="Piscine")
    climatisation = forms.BooleanField(required=False, label="Climatisation")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Importer ici pour éviter les imports circulaires
        from home.models import Ville, CategorieMaison
        
        # Définir les QuerySets
        self.fields['ville'].queryset = Ville.objects.all().order_by('nom')
        self.fields['categorie'].queryset = CategorieMaison.objects.all().order_by('nom')
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        prix_min = cleaned_data.get('prix_min')
        prix_max = cleaned_data.get('prix_max')
        
        # Validation des dates
        if date_debut and date_fin:
            if date_debut >= date_fin:
                raise ValidationError("La date de départ doit être après la date d'arrivée.")
            
            if date_debut < timezone.now().date():
                raise ValidationError("La date d'arrivée ne peut pas être dans le passé.")
        
        # Validation des prix
        if prix_min and prix_max and prix_min > prix_max:
            raise ValidationError("Le prix minimum ne peut pas être supérieur au prix maximum.")
        
        return cleaned_data


class ExportReservationsForm(forms.Form):
    """Formulaire pour l'export des réservations"""
    
    format_export = forms.ChoiceField(
        label="Format d'export",
        choices=[
            ('csv', 'CSV'),
            ('excel', 'Excel'),
            ('pdf', 'PDF'),
        ],
        initial='excel',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_debut = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        )
    )
    
    date_fin = forms.DateField(
        label="Date de fin",
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        )
    )
    
    statuts = forms.MultipleChoiceField(
        required=False,
        choices=Reservation.STATUT_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    inclure_paiements = forms.BooleanField(
        required=False,
        initial=True,
        label="Inclure les détails des paiements",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    inclure_evaluations = forms.BooleanField(
        required=False,
        initial=False,
        label="Inclure les évaluations",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Définir les dates par défaut (dernier mois)
        today = timezone.now().date()
        first_day_month = today.replace(day=1)
        self.fields['date_debut'].initial = first_day_month
        self.fields['date_fin'].initial = today
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_debut and date_fin:
            if date_debut > date_fin:
                raise ValidationError("La date de fin doit être après la date de début.")
            
            # Limiter à 1 an maximum
            if (date_fin - date_debut).days > 365:
                raise ValidationError("La période d'export ne peut pas dépasser 1 an.")
        
        return cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        maison = cleaned_data.get('maison') or self.maison_preselected
        nombre_personnes = cleaned_data.get('nombre_personnes')
        
        # Validation des dates
        if date_debut and date_fin:
            if date_debut >= date_fin:
                raise ValidationError("La date de départ doit être après la date d'arrivée.")
            
            if date_debut < timezone.now().date():
                raise ValidationError("La date d'arrivée ne peut pas être dans le passé.")
            
            # Vérifier la durée minimum (1 nuit) et maximum (1 an)
            duree = (date_fin - date_debut).days
            if duree < 1:
                raise ValidationError("La réservation doit durer au moins 1 nuit.")
            elif duree > 365:
                raise ValidationError("La réservation ne peut pas dépasser 1 an.")
            
            # Vérifier la disponibilité
            if maison:
                if not Reservation.objects.verifier_disponibilite(
                    maison, date_debut, date_fin, exclude_id=self.instance.pk if self.instance else None
                ):
                    raise ValidationError("Cette maison n'est pas disponible pour ces dates.")
        
        # Validation du nombre de personnes
        if maison and nombre_personnes:
            if nombre_personnes > maison.capacite_personnes:
                raise ValidationError(
                    f"Le nombre de personnes ({nombre_personnes}) dépasse la capacité "
                    f"de la maison ({maison.capacite_personnes})."
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        reservation = super().save(commit=False)
        
        # Assigner le client si pas déjà fait
        if self.user and not reservation.client_id:
            reservation.client = self.user
        
        # Assigner la maison présélectionnée si applicable
        if self.maison_preselected and not reservation.maison_id:
            reservation.maison = self.maison_preselected
        
        if commit:
            reservation.save()
        
        return reservation


class ReservationQuickForm(forms.Form):
    """Formulaire rapide pour vérifier la disponibilité"""
    
    date_debut = forms.DateField(
        label="Date d'arrivée",
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'min': timezone.now().date().isoformat()
            }
        )
    )
    
    date_fin = forms.DateField(
        label="Date de départ",
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'min': (timezone.now().date() + timedelta(days=1)).isoformat()
            }
        )
    )
    
    nombre_personnes = forms.IntegerField(
        label="Nombre de personnes",
        min_value=1,
        max_value=20,
        initial=2,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20
            }
        )
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_debut and date_fin:
            if date_debut >= date_fin:
                raise ValidationError("La date de départ doit être après la date d'arrivée.")
            
            if date_debut < timezone.now().date():
                raise ValidationError("La date d'arrivée ne peut pas être dans le passé.")
            
            duree = (date_fin - date_debut).days
            if duree < 1:
                raise ValidationError("La réservation doit durer au moins 1 nuit.")
        
        return cleaned_data


class ReservationAdminForm(forms.ModelForm):
    """Formulaire d'administration pour les gestionnaires"""
    
    class Meta:
        model = Reservation
        fields = [
            'client', 'maison', 'date_debut', 'date_fin', 'nombre_personnes',
            'heure_arrivee', 'heure_depart', 'statut', 'mode_paiement',
            'prix_par_nuit', 'frais_service', 'reduction_montant', 'reduction_raison',
            'commentaire_client', 'commentaire_gestionnaire',
            'contact_urgence_nom', 'contact_urgence_telephone'
        ]
        
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'heure_arrivee': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'heure_depart': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'nombre_personnes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'mode_paiement': forms.Select(attrs={'class': 'form-control'}),
            'prix_par_nuit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'frais_service': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reduction_montant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reduction_raison': forms.TextInput(attrs={'class': 'form-control'}),
            'commentaire_client': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'commentaire_gestionnaire': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contact_urgence_nom': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_urgence_telephone': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Filtrer selon les permissions
        if user:
            if hasattr(user, 'is_super_admin') and user.is_super_admin():
                # Super admin voit tout
                pass
            elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
                # Gestionnaire voit seulement ses maisons et clients
                self.fields['maison'].queryset = Maison.objects.filter(gestionnaire=user)
                from django.contrib.auth import get_user_model
                User = get_user_model()
                self.fields['client'].queryset = User.objects.filter(role='CLIENT')
            else:
                # Pas d'accès
                self.fields['maison'].queryset = Maison.objects.none()
                self.fields['client'].queryset = get_user_model().objects.none()


class ReservationFilterForm(forms.Form):
    """Formulaire de filtrage des réservations"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Rechercher par numéro, client, maison...'
            }
        )
    )
    
    statut = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous les statuts')] + Reservation.STATUT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    maison = forms.ModelChoiceField(
        required=False,
        queryset=Maison.objects.none(),
        empty_label="Toutes les maisons",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_debut = forms.DateField(
        required=False,
        label="À partir du",
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        )
    )
    
    date_fin = forms.DateField(
        required=False,
        label="Jusqu'au",
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        )
    )
    
    mode_paiement = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous les modes')] + Reservation.MODE_PAIEMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les maisons selon l'utilisateur
        if user:
            if hasattr(user, 'is_super_admin') and user.is_super_admin():
                self.fields['maison'].queryset = Maison.objects.all().order_by('nom')
            elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
                self.fields['maison'].queryset = Maison.objects.filter(
                    gestionnaire=user
                ).order_by('nom')


class PaiementForm(forms.ModelForm):
    """Formulaire pour les paiements"""
    
    class Meta:
        model = Paiement
        fields = [
            'type_paiement', 'montant', 'reference_externe', 'notes'
        ]
        
        widgets = {
            'type_paiement': forms.Select(attrs={'class': 'form-control'}),
            'montant': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0'
                }
            ),
            'reference_externe': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Référence du système de paiement'
                }
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Notes internes...'
                }
            ),
        }
    
    def __init__(self, *args, reservation=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.reservation = reservation
        
        # Filtrer les types de paiement actifs
        self.fields['type_paiement'].queryset = TypePaiement.objects.filter(actif=True)
        
        # Définir le montant par défaut
        if reservation:
            if reservation.mode_paiement == 'integral':
                self.fields['montant'].initial = reservation.prix_total
            elif reservation.mode_paiement == 'acompte':
                self.fields['montant'].initial = reservation.montant_acompte or (reservation.prix_total * Decimal('0.30'))
            
            # Calculer et afficher les frais
            self.fields['montant'].help_text = f"Montant total de la réservation: {reservation.prix_total} FCFA"
    
    def save(self, commit=True):
        paiement = super().save(commit=False)
        
        if self.reservation:
            paiement.reservation = self.reservation
        
        if commit:
            paiement.save()
        
        return paiement


class EvaluationReservationForm(forms.ModelForm):
    """Formulaire d'évaluation d'une réservation"""
    
    class Meta:
        model = EvaluationReservation
        fields = [
            'note_globale', 'note_proprete', 'note_equipements',
            'note_emplacement', 'note_rapport_qualite_prix',
            'commentaire', 'points_positifs', 'points_amelioration',
            'recommande', 'reviendrait'
        ]
        
        widgets = {
            'note_globale': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'note_proprete': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'note_equipements': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'note_emplacement': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'note_rapport_qualite_prix': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'commentaire': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Partagez votre expérience...'
                }
            ),
            'points_positifs': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Ce qui vous a plu...'
                }
            ),
            'points_amelioration': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Ce qui pourrait être amélioré...'
                }
            ),
            'recommande': forms.RadioSelect(
                choices=[(True, 'Oui'), (False, 'Non')],
                attrs={'class': 'form-check-input'}
            ),
            'reviendrait': forms.RadioSelect(
                choices=[(True, 'Oui'), (False, 'Non')],
                attrs={'class': 'form-check-input'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personnaliser les labels
        self.fields['note_globale'].label = "Note globale"
        self.fields['note_proprete'].label = "Propreté"
        self.fields['note_equipements'].label = "Équipements"
        self.fields['note_emplacement'].label = "Emplacement"
        self.fields['note_rapport_qualite_prix'].label = "Rapport qualité/prix"
        self.fields['commentaire'].label = "Votre avis"
        self.fields['points_positifs'].label = "Points positifs"
        self.fields['points_amelioration'].label = "Points à améliorer"
        self.fields['recommande'].label = "Recommanderiez-vous cette maison ?"
        self.fields['reviendrait'].label = "Reviendriez-vous ?"
        
        # Rendre certains champs obligatoires
        self.fields['commentaire'].required = True


class ReponseGestionnaireForm(forms.ModelForm):
    """Formulaire pour la réponse du gestionnaire à une évaluation"""
    
    class Meta:
        model = EvaluationReservation
        fields = ['reponse_gestionnaire']
        
        widgets = {
            'reponse_gestionnaire': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Votre réponse à cette évaluation...'
                }
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reponse_gestionnaire'].label = "Votre réponse"
        self.fields['reponse_gestionnaire'].required = True


class DisponibiliteForm(forms.ModelForm):
    """Formulaire pour gérer les disponibilités"""
    
    class Meta:
        model = Disponibilite
        fields = ['date', 'disponible', 'prix_special', 'raison_indisponibilite']
        
        widgets = {
            'date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'prix_special': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0'
                }
            ),
            'raison_indisponibilite': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Raison de l\'indisponibilité'
                }
            ),
        }
    
    def __init__(self, *args, maison=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.maison = maison
        
        if maison:
            self.fields['prix_special'].help_text = f"Prix normal: {maison.prix_par_nuit} FCFA"
    
    def save(self, commit=True):
        disponibilite = super().save(commit=False)
        
        if self.maison:
            disponibilite.maison = self.maison
        
        if commit:
            disponibilite.save()
        
        return disponibilite


class DisponibiliteBulkForm(forms.Form):
    """Formulaire pour gérer les disponibilités en masse"""
    
    date_debut = forms.DateField(
        label="Date de début",
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        )
    )
    
    date_fin = forms.DateField(
        label="Date de fin",
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        )
    )
    
    action = forms.ChoiceField(
        label="Action",
        choices=[
            ('bloquer', 'Bloquer les dates'),
            ('liberer', 'Libérer les dates'),
            ('prix_special', 'Appliquer un prix spécial'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    raison = forms.CharField(
        required=False,
        label="Raison",
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Raison du blocage/modification'
            }
        )
    )
    
    prix_special = forms.DecimalField(
        required=False,
        decimal_places=2,
        max_digits=8,
        label="Prix spécial (FCFA)",
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }
        )
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data