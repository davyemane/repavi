# home/forms.py - Version adaptée avec nouveaux rôles
from django import forms
from django.contrib.auth import get_user_model
from .models import Ville, CategorieMaison, Maison, PhotoMaison, Reservation

User = get_user_model()


class VilleForm(forms.ModelForm):
    class Meta:
        model = Ville
        fields = ['nom', 'code_postal', 'departement', 'pays']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Nom de la ville'
            }),
            'code_postal': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': '75001'
            }),
            'departement': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Nom du département'
            }),
            'pays': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'value': 'France'
            }),
        }


class CategorieMaisonForm(forms.ModelForm):
    COULEUR_CHOICES = [
        ('blue', 'Bleu'),
        ('green', 'Vert'),
        ('purple', 'Violet'),
        ('red', 'Rouge'),
        ('yellow', 'Jaune'),
        ('indigo', 'Indigo'),
        ('pink', 'Rose'),
        ('gray', 'Gris'),
    ]
    
    couleur = forms.ChoiceField(
        choices=COULEUR_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    
    class Meta:
        model = CategorieMaison
        fields = ['nom', 'description', 'couleur']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Villa, Appartement, Maison...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 3,
                'placeholder': 'Description de la catégorie...'
            }),
        }


class MaisonForm(forms.ModelForm):
    """Formulaire pour les maisons - ADAPTÉ avec gestionnaire"""
    
    class Meta:
        model = Maison
        fields = [
            'nom', 'description', 'adresse', 'ville', 'capacite_personnes',
            'nombre_chambres', 'nombre_salles_bain', 'superficie', 'prix_par_nuit',
            'disponible', 'featured', 'categorie', 'wifi', 'parking', 'piscine',
            'jardin', 'climatisation', 'lave_vaisselle', 'machine_laver',
            'gestionnaire', 'slug'
        ]
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Nom de la maison'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 4,
                'placeholder': 'Description détaillée de la maison...'
            }),
            'adresse': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': '123 Rue de la République'
            }),
            'ville': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'capacite_personnes': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': 1,
                'max': 20
            }),
            'nombre_chambres': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': 1,
                'max': 10
            }),
            'nombre_salles_bain': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': 1,
                'max': 10
            }),
            'superficie': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': 20,
                'placeholder': 'Superficie en m²'
            }),
            'prix_par_nuit': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': 10,
                'step': '0.01',
                'placeholder': 'Prix en euros'
            }),
            'categorie': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'gestionnaire': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'URL slug (auto-généré)'
            }),
            # Checkboxes pour les équipements
            'disponible': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'featured': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'wifi': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'parking': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'piscine': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'jardin': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'climatisation': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'lave_vaisselle': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'machine_laver': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrer les gestionnaires disponibles selon les permissions
        if user:
            if user.is_super_admin():
                # Super admin peut assigner n'importe quel gestionnaire
                self.fields['gestionnaire'].queryset = User.objects.filter(
                    role__in=['GESTIONNAIRE', 'SUPER_ADMIN']
                )
            elif user.is_gestionnaire():
                # Gestionnaire ne peut s'assigner que lui-même
                self.fields['gestionnaire'].queryset = User.objects.filter(id=user.id)
                self.fields['gestionnaire'].initial = user
            else:
                # Autres utilisateurs ne peuvent pas créer de maisons
                self.fields['gestionnaire'].queryset = User.objects.none()


class PhotoMaisonForm(forms.ModelForm):
    class Meta:
        model = PhotoMaison
        fields = ['maison', 'image', 'titre', 'principale', 'ordre']
        widgets = {
            'maison': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'accept': 'image/*'
            }),
            'titre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Titre de la photo'
            }),
            'ordre': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': 0,
                'value': 0
            }),
            'principale': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrer les maisons selon les permissions
        if user and not user.is_super_admin():
            self.fields['maison'].queryset = Maison.objects.filter(gestionnaire=user)


class ReservationForm(forms.ModelForm):
    """Formulaire pour les réservations - ADAPTÉ avec client"""
    
    class Meta:
        model = Reservation
        fields = [
            'maison', 'client', 'date_debut', 'date_fin', 'nombre_personnes',
            'prix_total', 'statut', 'telephone', 'message'
        ]
        widgets = {
            'maison': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'client': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'date_debut': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'type': 'date'
            }),
            'date_fin': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'type': 'date'
            }),
            'nombre_personnes': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': 1
            }),
            'prix_total': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'step': '0.01',
                'readonly': True
            }),
            'statut': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': '+33 1 23 45 67 89'
            }),
            'message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 3,
                'placeholder': 'Message du client...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrer selon les permissions utilisateur
        if user:
            if user.is_super_admin():
                # Super admin voit tout
                self.fields['client'].queryset = User.objects.filter(role='CLIENT')
                self.fields['maison'].queryset = Maison.objects.all()
            elif user.is_gestionnaire():
                # Gestionnaire voit ses maisons et tous les clients
                self.fields['client'].queryset = User.objects.filter(role='CLIENT')
                self.fields['maison'].queryset = Maison.objects.filter(gestionnaire=user)
            elif user.is_client():
                # Client ne peut réserver que pour lui-même
                self.fields['client'].queryset = User.objects.filter(id=user.id)
                self.fields['client'].initial = user
                self.fields['client'].widget = forms.HiddenInput()
                self.fields['maison'].queryset = Maison.objects.filter(disponible=True)
                # Masquer certains champs pour les clients
                self.fields['statut'].widget = forms.HiddenInput()
                self.fields['prix_total'].widget = forms.HiddenInput()


# Formulaire de recherche/filtre - ADAPTÉ
class MaisonFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Rechercher une maison...'
        })
    )
    ville = forms.ModelChoiceField(
        queryset=Ville.objects.all(),
        required=False,
        empty_label="Toutes les villes",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    categorie = forms.ModelChoiceField(
        queryset=CategorieMaison.objects.all(),
        required=False,
        empty_label="Toutes les catégories",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    disponible = forms.ChoiceField(
        choices=[('', 'Tous'), ('True', 'Disponible'), ('False', 'Indisponible')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    featured = forms.ChoiceField(
        choices=[('', 'Tous'), ('True', 'Featured'), ('False', 'Non featured')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    prix_min = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Prix min €'
        })
    )
    prix_max = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Prix max €'
        })
    )
    capacite_min = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Personnes min'
        })
    )


# NOUVEAU : Formulaire de réservation pour clients
class ClientReservationForm(forms.Form):
    """Formulaire simplifié pour les clients sur la page publique"""
    
    date_debut = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'type': 'date',
            'id': 'date_debut'
        }),
        label='Date d\'arrivée'
    )
    
    date_fin = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'type': 'date',
            'id': 'date_fin'
        }),
        label='Date de départ'
    )
    
    nombre_personnes = forms.IntegerField(
        min_value=1,
        max_value=20,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'id': 'nombre_personnes'
        }),
        label='Nombre de personnes'
    )
    
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'rows': 3,
            'placeholder': 'Message pour le gestionnaire (optionnel)...'
        }),
        label='Message'
    )
    
    telephone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Votre numéro de téléphone'
        }),
        label='Téléphone'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_debut and date_fin:
            if date_debut >= date_fin:
                raise forms.ValidationError("La date de départ doit être postérieure à la date d'arrivée.")
            
            # Vérifier que la date de début n'est pas dans le passé
            from django.utils import timezone
            if date_debut < timezone.now().date():
                raise forms.ValidationError("La date d'arrivée ne peut pas être dans le passé.")
        
        return cleaned_data


# NOUVEAU : Formulaire de contact
class ContactForm(forms.Form):
    """Formulaire de contact"""
    
    nom = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Votre nom'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'votre@email.com'
        })
    )
    
    sujet = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Sujet de votre message'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'rows': 6,
            'placeholder': 'Votre message...'
        })
    )
    
    type_demande = forms.ChoiceField(
        choices=[
            ('info', 'Demande d\'information'),
            ('reservation', 'Question sur une réservation'),
            ('gestionnaire', 'Devenir gestionnaire'),
            ('support', 'Support technique'),
            ('autre', 'Autre')
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        }),
        label='Type de demande'
    )