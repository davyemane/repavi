# reservations/forms.py - Formulaires pour les réservations

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from .models import Reservation, Paiement, TypePaiement, EvaluationReservation, Disponibilite
from home.models import Maison
from django.contrib.auth import get_user_model

from .models import Attribution

User = get_user_model()


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

        if maison:
            self.fields['nombre_personnes'].widget.attrs['max'] = maison.capacite_personnes
            self.fields['nombre_personnes'].help_text = f"Maximum {maison.capacite_personnes} personnes"

        self.fields['date_debut'].help_text = "Date d'arrivée"
        self.fields['date_fin'].help_text = "Date de départ"
        self.fields['nombre_personnes'].help_text = "Nombre total de personnes"
        self.fields['heure_arrivee'].help_text = "Heure d'arrivée prévue"
        self.fields['heure_depart'].help_text = "Heure de départ prévue"
        self.fields['contact_urgence_nom'].help_text = "Personne à contacter en cas d'urgence"
        self.fields['contact_urgence_telephone'].help_text = "Numéro de téléphone du contact d'urgence"

        self.fields['contact_urgence_nom'].required = True
        self.fields['contact_urgence_telephone'].required = True

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        nombre_personnes = cleaned_data.get('nombre_personnes')

        if date_debut and date_fin:
            if date_debut >= date_fin:
                raise ValidationError("La date de fin doit être après la date de début.")

            if date_debut < timezone.now().date():
                raise ValidationError("La date de début ne peut pas être dans le passé.")

            if (date_fin - date_debut).days > 365:
                raise ValidationError("La période ne peut pas dépasser 1 an.")

            if (date_fin - date_debut).days < 1:
                raise ValidationError("La réservation doit être d'au moins 1 nuit.")

        if self.maison_preselected and nombre_personnes:
            if nombre_personnes > self.maison_preselected.capacite_personnes:
                raise ValidationError(
                    f"Le nombre de personnes ne peut pas dépasser {self.maison_preselected.capacite_personnes}."
                )

        if self.maison_preselected and date_debut and date_fin:
            exclude_id = self.instance.pk if self.instance.pk else None
            if not Reservation.objects.verifier_disponibilite(
                self.maison_preselected,
                date_debut,
                date_fin,
                exclude_id=exclude_id
            ):
                raise ValidationError("Cette maison n'est pas disponible pour ces dates.")

        return cleaned_data

    def save(self, commit=True):
        reservation = super().save(commit=False)

        # Assigner les valeurs nécessaires
        if self.user:
            reservation.client = self.user
        if self.maison_preselected:
            reservation.maison = self.maison_preselected

        # Calculer les valeurs dérivées - MODIFIÉ POUR ENTIERS
        if reservation.date_debut and reservation.date_fin:
            reservation.nombre_nuits = (reservation.date_fin - reservation.date_debut).days
            if reservation.maison:
                reservation.prix_par_nuit = reservation.maison.prix_par_nuit
                # Prix total calculé en entiers
                reservation.prix_total = reservation.prix_par_nuit * reservation.nombre_nuits

        if commit:
            reservation.save()
                
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
    """Formulaire pour modifier une réservation - MODIFIÉ POUR ENTIERS"""
    
    class Meta:
        model = Reservation
        fields = [
            'date_debut', 'date_fin', 'nombre_personnes',
            'heure_arrivee', 'heure_depart', 'commentaire_client'
        ]
        
        widgets = {
            'date_debut': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'date_fin': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'nombre_personnes': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 1}
            ),
            'heure_arrivee': forms.TimeInput(
                attrs={'type': 'time', 'class': 'form-control'}
            ),
            'heure_depart': forms.TimeInput(
                attrs={'type': 'time', 'class': 'form-control'}
            ),
            'commentaire_client': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.maison:
            self.fields['nombre_personnes'].widget.attrs['max'] = self.instance.maison.capacite_personnes

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_debut and date_fin:
            if date_debut >= date_fin:
                raise ValidationError("La date de fin doit être après la date de début.")
            
            if date_debut < timezone.now().date():
                raise ValidationError("La date de début ne peut pas être dans le passé.")
            
            # Vérifier la disponibilité
            if self.instance and self.instance.maison:
                if not Reservation.objects.verifier_disponibilite(
                    self.instance.maison,
                    date_debut,
                    date_fin,
                    exclude_id=self.instance.pk
                ):
                    raise ValidationError("Cette maison n'est pas disponible pour ces nouvelles dates.")
        
        return cleaned_data

    def save(self, commit=True):
        reservation = super().save(commit=False)
        
        # Recalculer les prix - MODIFIÉ POUR ENTIERS
        if reservation.date_debut and reservation.date_fin and reservation.maison:
            reservation.nombre_nuits = (reservation.date_fin - reservation.date_debut).days
            reservation.prix_total = reservation.prix_par_nuit * reservation.nombre_nuits
        
        if commit:
            reservation.save()
        
        return reservation

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
    """Formulaire pour ajouter un paiement - MODIFIÉ POUR ENTIERS"""
    
    class Meta:
        model = Paiement
        fields = ['type_paiement', 'montant', 'reference_externe', 'notes']
        
        widgets = {
            'type_paiement': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'montant': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 1,
                    'step': 1,  # CHANGÉ: étape de 1 pour les entiers
                    'placeholder': 'Montant en FCFA'
                }
            ),
            'reference_externe': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Référence du paiement'
                }
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Notes ou commentaires sur ce paiement'
                }
            )
        }

    def __init__(self, *args, reservation=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.reservation = reservation
        
        # Filtrer les types de paiement actifs
        self.fields['type_paiement'].queryset = TypePaiement.objects.filter(actif=True)
        
        if reservation:
            # Suggérer le montant restant à payer
            montant_restant = reservation.montant_restant
            if montant_restant > 0:
                self.fields['montant'].widget.attrs['value'] = montant_restant
                self.fields['montant'].help_text = f"Montant restant à payer: {montant_restant:,} FCFA"
            
            # Limiter le montant maximum
            self.fields['montant'].widget.attrs['max'] = montant_restant

    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        
        if not montant or montant <= 0:
            raise ValidationError("Le montant doit être supérieur à 0.")
        
        if self.reservation:
            montant_restant = self.reservation.montant_restant
            if montant > montant_restant:
                raise ValidationError(
                    f"Le montant ne peut pas dépasser le montant restant à payer ({montant_restant:,} FCFA)."
                )
        
        return montant

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
    """Formulaire pour gérer la disponibilité d'une maison - MODIFIÉ POUR ENTIERS"""
    
    class Meta:
        model = Disponibilite
        fields = ['date', 'disponible', 'prix_special', 'raison_indisponibilite']
        
        widgets = {
            'date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'disponible': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'prix_special': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 0,
                    'step': 1,  # CHANGÉ: étape de 1 pour les entiers
                    'placeholder': 'Prix spécial en FCFA'
                }
            ),
            'raison_indisponibilite': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Raison de l\'indisponibilité'
                }
            )
        }

    def __init__(self, *args, maison=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.maison = maison
        
        if maison:
            self.fields['prix_special'].help_text = f"Prix normal: {maison.prix_par_nuit:,} FCFA"

    def clean_date(self):
        date = self.cleaned_data.get('date')
        
        if date and date < timezone.now().date():
            raise ValidationError("Impossible de modifier la disponibilité pour une date passée.")
        
        return date

    def clean_prix_special(self):
        prix_special = self.cleaned_data.get('prix_special')
        
        if prix_special is not None and prix_special < 0:
            raise ValidationError("Le prix spécial ne peut pas être négatif.")
        
        return prix_special

    def save(self, commit=True):
        disponibilite = super().save(commit=False)
        
        if self.maison:
            disponibilite.maison = self.maison
        
        if commit:
            disponibilite.save()
        
        return disponibilite


class ExportReservationsForm(forms.Form):
    """Formulaire pour exporter les réservations"""
    
    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
    ]
    
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('confirmee', 'Confirmée'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    
    format_export = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Format d'export"
    )
    
    date_debut = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Date de début",
        help_text="Date de création des réservations"
    )
    
    date_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Date de fin",
        help_text="Date de création des réservations"
    )
    
    statuts = forms.MultipleChoiceField(
        choices=STATUT_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Statuts à inclure",
        help_text="Laisser vide pour inclure tous les statuts"
    )
    
    inclure_paiements = forms.BooleanField(
        required=False,
        initial=True,
        label="Inclure les informations de paiement"
    )
    
    inclure_evaluations = forms.BooleanField(
        required=False,
        initial=False,
        label="Inclure les évaluations"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dates par défaut (dernier mois)
        today = timezone.now().date()
        debut_mois = today.replace(day=1)
        
        self.fields['date_debut'].initial = debut_mois
        self.fields['date_fin'].initial = today

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_debut and date_fin:
            if date_debut > date_fin:
                raise ValidationError("La date de début doit être antérieure à la date de fin.")
            
            # Limiter la période à 1 an
            if (date_fin - date_debut).days > 365:
                raise ValidationError("La période d'export ne peut pas dépasser 1 an.")
        
        return cleaned_data


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



class AttributionEtape1Form(forms.Form):
    """
    Étape 1 : Sélectionner ou créer un client
    """
    OPTION_CHOICES = [
        ('existant', 'Client existant'),
        ('nouveau', 'Nouveau client'),
    ]
    
    option_client = forms.ChoiceField(
        choices=OPTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-radio'}),
        label="Type de client"
    )
    
    # Pour client existant
    client_existant = forms.ModelChoiceField(
        queryset=None,  # Défini dans __init__
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-placeholder': 'Rechercher un client...'
        }),
        label="Sélectionner un client"
    )
    
    # Pour nouveau client
    prenom = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prénom'
        }),
        label="Prénom"
    )
    
    nom = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom de famille'
        }),
        label="Nom"
    )
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@exemple.com'
        }),
        label="Email"
    )
    
    telephone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+237 6XX XXX XXX'
        }),
        label="Téléphone"
    )
    
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom d\'utilisateur unique'
        }),
        label="Nom d'utilisateur"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer seulement les clients
        self.fields['client_existant'].queryset = User.objects.filter(
            role='CLIENT'
        ).order_by('first_name', 'last_name')
    
    def clean(self):
        cleaned_data = super().clean()
        option = cleaned_data.get('option_client')
        
        if option == 'existant':
            if not cleaned_data.get('client_existant'):
                raise ValidationError("Veuillez sélectionner un client existant.")
        
        elif option == 'nouveau':
            # Vérifier que tous les champs requis sont remplis
            required_fields = ['prenom', 'nom', 'email', 'telephone', 'username']
            for field in required_fields:
                if not cleaned_data.get(field):
                    raise ValidationError(f"Le champ {field} est requis pour un nouveau client.")
            
            # Vérifier l'unicité de l'email et du username
            email = cleaned_data.get('email')
            username = cleaned_data.get('username')
            
            if email and User.objects.filter(email=email).exists():
                raise ValidationError("Un utilisateur avec cet email existe déjà.")
            
            if username and User.objects.filter(username=username).exists():
                raise ValidationError("Ce nom d'utilisateur est déjà pris.")
        
        return cleaned_data
    
    def get_or_create_client(self):
        """Retourne le client sélectionné ou crée un nouveau client"""
        cleaned_data = self.cleaned_data
        
        if cleaned_data['option_client'] == 'existant':
            return cleaned_data['client_existant']
        
        else:  # nouveau client
            client = User.objects.create_user(
                username=cleaned_data['username'],
                email=cleaned_data['email'],
                first_name=cleaned_data['prenom'],
                last_name=cleaned_data['nom'],
                telephone=cleaned_data['telephone'],
                role='CLIENT',
                password='temp123456',  # Mot de passe temporaire
                is_active=True
            )
            
            # Créer le profil client si disponible
            try:
                from users.models import ProfilClient
                ProfilClient.objects.create(user=client)
            except ImportError:
                pass
            
            return client


class AttributionEtape2Form(forms.ModelForm):
    """
    Étape 2 : Attribuer une maison au client
    """
    
    class Meta:
        model = Attribution
        fields = [
            'maison', 'date_entree', 'date_sortie', 
            'montant_total', 'montant_paye', 'notes_admin'
        ]
        
        widgets = {
            'maison': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Sélectionner une maison...'
            }),
            'date_entree': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'min': timezone.now().date().isoformat()
            }),
            'date_sortie': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'min': (timezone.now().date() + timedelta(days=1)).isoformat()
            }),
            'montant_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '0',
                'placeholder': 'Montant total en FCFA'
            }),
            'montant_paye': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '0',
                'placeholder': 'Montant déjà payé en FCFA'
            }),
            'notes_admin': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes internes sur cette attribution...'
            }),
        }
    
    def __init__(self, *args, gestionnaire=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les maisons selon les permissions
        if gestionnaire:
            if hasattr(gestionnaire, 'is_super_admin') and gestionnaire.is_super_admin():
                # Super admin voit toutes les maisons libres
                self.fields['maison'].queryset = Maison.objects.filter(
                    disponible=True,
                    statut_occupation='libre'
                ).order_by('numero', 'nom')
            else:
                # Gestionnaire voit seulement ses maisons libres
                self.fields['maison'].queryset = Maison.objects.filter(
                    gestionnaire=gestionnaire,
                    disponible=True,
                    statut_occupation='libre'
                ).order_by('numero', 'nom')
        
        # Ajouter l'aide contextuelle
        self.fields['date_entree'].help_text = "Date d'entrée prévue"
        self.fields['date_sortie'].help_text = "Date de sortie prévue"
        self.fields['montant_total'].help_text = "Sera calculé automatiquement si vide"
        self.fields['montant_paye'].help_text = "Montant déjà payé par le client"
    
    def clean(self):
        cleaned_data = super().clean()
        date_entree = cleaned_data.get('date_entree')
        date_sortie = cleaned_data.get('date_sortie')
        maison = cleaned_data.get('maison')
        montant_paye = cleaned_data.get('montant_paye', 0)
        
        # Vérification des dates
        if date_entree and date_sortie:
            if date_entree >= date_sortie:
                raise ValidationError("La date de sortie doit être après la date d'entrée.")
            
            if date_entree < timezone.now().date():
                raise ValidationError("La date d'entrée ne peut pas être dans le passé.")
            
            # Vérifier la disponibilité de la maison pour ces dates
            if maison:
                conflits = Attribution.objects.filter(
                    maison=maison,
                    statut='en_cours',
                    date_entree__lt=date_sortie,
                    date_sortie__gt=date_entree
                )
                
                if self.instance.pk:
                    conflits = conflits.exclude(pk=self.instance.pk)
                
                if conflits.exists():
                    conflit = conflits.first()
                    raise ValidationError(
                        f"Cette maison est déjà attribuée à {conflit.client.first_name} "
                        f"du {conflit.date_entree.strftime('%d/%m/%Y')} au {conflit.date_sortie.strftime('%d/%m/%Y')}"
                    )
        
        # Calculer le montant total si pas fourni
        if not cleaned_data.get('montant_total') and maison and date_entree and date_sortie:
            duree = (date_sortie - date_entree).days
            cleaned_data['montant_total'] = maison.prix_par_nuit * duree
        
        # Vérifier que le montant payé ne dépasse pas le total
        montant_total = cleaned_data.get('montant_total', 0)
        if montant_paye > montant_total:
            raise ValidationError("Le montant payé ne peut pas dépasser le montant total.")
        
        return cleaned_data


class AttributionDirecteForm(forms.ModelForm):
    """
    Formulaire complet pour créer une attribution directe
    (combine les 2 étapes en une seule vue si préféré)
    """
    
    client = forms.ModelChoiceField(
        queryset=None,  # Défini dans __init__
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': 'Rechercher un client...'
        }),
        label="Client"
    )
    
    class Meta:
        model = Attribution
        fields = [
            'client', 'maison', 'date_entree', 'date_sortie',
            'montant_total', 'montant_paye', 'notes_admin'
        ]
        
        widgets = {
            'maison': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Sélectionner une maison...'
            }),
            'date_entree': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'date_sortie': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'montant_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '0'
            }),
            'montant_paye': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '0'
            }),
            'notes_admin': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les clients
        self.fields['client'].queryset = User.objects.filter(
            role='CLIENT'
        ).order_by('first_name', 'last_name')
        
        # Filtrer les maisons selon les permissions
        if user:
            if hasattr(user, 'is_super_admin') and user.is_super_admin():
                self.fields['maison'].queryset = Maison.objects.filter(
                    disponible=True,
                    statut_occupation='libre'
                ).order_by('numero', 'nom')
            else:
                self.fields['maison'].queryset = Maison.objects.filter(
                    gestionnaire=user,
                    disponible=True,
                    statut_occupation='libre'
                ).order_by('numero', 'nom')


class AttributionFilterForm(forms.Form):
    """
    Formulaire de filtrage pour le tableau de suivi
    """
    client = forms.ModelChoiceField(
        queryset=None,  # Défini dans __init__
        required=False,
        empty_label="Tous les clients",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Client"
    )
    
    maison = forms.ModelChoiceField(
        queryset=None,  # Défini dans __init__
        required=False,
        empty_label="Toutes les maisons",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Maison"
    )
    
    statut = forms.ChoiceField(
        choices=[('', 'Tous les statuts')] + Attribution.STATUT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Statut"
    )
    
    type_attribution = forms.ChoiceField(
        choices=[('', 'Tous les types')] + Attribution.TYPE_ATTRIBUTION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Type"
    )
    
    date_debut = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label="Date d'entrée à partir du"
    )
    
    date_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label="Date d'entrée jusqu'au"
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par nom, prénom, maison...'
        }),
        label="Recherche"
    )
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if user:
            # Filtrer selon les permissions
            if hasattr(user, 'is_super_admin') and user.is_super_admin():
                clients_qs = User.objects.filter(role='CLIENT').order_by('first_name', 'last_name')
                maisons_qs = Maison.objects.all().order_by('numero', 'nom')
            else:
                # Pour les gestionnaires, filtrer les clients qui ont des attributions dans leurs maisons
                attributions_user = Attribution.objects.filter(maison__gestionnaire=user)
                clients_ids = attributions_user.values_list('client', flat=True).distinct()
                clients_qs = User.objects.filter(id__in=clients_ids).order_by('first_name', 'last_name')
                maisons_qs = Maison.objects.filter(gestionnaire=user).order_by('numero', 'nom')
            
            self.fields['client'].queryset = clients_qs
            self.fields['maison'].queryset = maisons_qs