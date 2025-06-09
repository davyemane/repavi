# home/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Ville, CategorieMaison, Maison, PhotoMaison, Reservation

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
    class Meta:
        model = Maison
        fields = [
            'nom', 'description', 'adresse', 'ville', 'capacite_personnes',
            'nombre_chambres', 'nombre_salles_bain', 'superficie', 'prix_par_nuit',
            'disponible', 'featured', 'categorie', 'wifi', 'parking', 'piscine',
            'jardin', 'climatisation', 'lave_vaisselle', 'machine_laver',
            'proprietaire', 'slug'
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
            'proprietaire': forms.Select(attrs={
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

class PhotoMaisonForm(forms.ModelForm):
    class Meta:
        model = PhotoMaison
        fields = ['maison', 'image', 'titre', 'principale', 'ordre']
        widgets = {
            'maison': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
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

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            'maison', 'locataire', 'date_debut', 'date_fin', 'nombre_personnes',
            'prix_total', 'statut', 'telephone', 'message'
        ]
        widgets = {
            'maison': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'locataire': forms.Select(attrs={
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
                'step': '0.01'
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

# Formulaire de recherche/filtre
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