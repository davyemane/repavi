# home/forms.py - Version adaptée avec nouveaux rôles et corrections

from django import forms
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from .models import Ville, CategorieMaison, Maison, PhotoMaison

User = get_user_model()

# ======== FORMULAIRES DE BASE ========

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
    """Formulaire pour les maisons - version simplifiée pour gestionnaires"""

    class Meta:
        model = Maison
        # Exclure complètement le gestionnaire, locataire_actuel et date_fin_location du formulaire
        exclude = ['gestionnaire', 'date_creation', 'date_modification', 'locataire_actuel', 'date_fin_location']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de la maison'}),
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: M001'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'ville': forms.Select(attrs={'class': 'form-control'}),
            'capacite_personnes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'nombre_chambres': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'nombre_salles_bain': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'superficie': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'prix_par_nuit': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'categorie': forms.Select(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Généré automatiquement si vide'}),
            'statut_occupation': forms.Select(attrs={'class': 'form-control'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'wifi': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'parking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'piscine': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'jardin': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'climatisation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lave_vaisselle': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'machine_laver': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'balcon': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'terrasse': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Rendre le slug optionnel
        self.fields['slug'].required = False
        self.fields['slug'].help_text = "Laissez vide pour génération automatique"
        
        # Définir la valeur par défaut pour statut_occupation
        if not self.instance.pk:  # Nouvelle instance
            self.fields['statut_occupation'].initial = 'libre'

    def clean_numero(self):
        numero = self.cleaned_data.get('numero')
        if numero:
            # Vérifier l'unicité du numéro
            qs = Maison.objects.filter(numero=numero)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Ce numéro de maison existe déjà.")
        return numero

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        nom = self.cleaned_data.get('nom')
        
        # Générer automatiquement si vide
        if not slug and nom:
            slug = slugify(nom)
        
        # Vérifier l'unicité
        if slug:
            qs = Maison.objects.filter(slug=slug)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                base_slug = slug
                counter = 1
                while Maison.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
        
        return slug

    def clean(self):
        cleaned_data = super().clean()
        capacite = cleaned_data.get('capacite_personnes')
        chambres = cleaned_data.get('nombre_chambres')
        
        # Validation : la capacité ne peut pas être inférieure au nombre de chambres
        if capacite and chambres and capacite < chambres:
            raise forms.ValidationError(
                "La capacité en personnes ne peut pas être inférieure au nombre de chambres."
            )
        
        return cleaned_data


class SuperAdminMaisonForm(forms.ModelForm):
    """Formulaire pour super admins avec sélection de gestionnaire"""
    
    class Meta:
        model = Maison
        exclude = ['date_creation', 'date_modification', 'locataire_actuel', 'date_fin_location']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: M001'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'ville': forms.Select(attrs={'class': 'form-control'}),
            'gestionnaire': forms.Select(attrs={'class': 'form-control'}),
            'capacite_personnes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'nombre_chambres': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'nombre_salles_bain': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'superficie': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'prix_par_nuit': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'categorie': forms.Select(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'statut_occupation': forms.Select(attrs={'class': 'form-control'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'wifi': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'parking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'piscine': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'jardin': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'climatisation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lave_vaisselle': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'machine_laver': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'balcon': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'terrasse': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrer les gestionnaires
        if 'gestionnaire' in self.fields:
            self.fields['gestionnaire'].queryset = User.objects.filter(role__in=['GESTIONNAIRE', 'SUPER_ADMIN'])
        
        # Rendre le slug optionnel
        self.fields['slug'].required = False
        self.fields['slug'].help_text = "Généré automatiquement si vide"
        
        # Définir la valeur par défaut pour statut_occupation
        if not self.instance.pk:  # Nouvelle instance
            self.fields['statut_occupation'].initial = 'libre'

    def clean_numero(self):
        numero = self.cleaned_data.get('numero')
        if numero:
            # Vérifier l'unicité du numéro
            qs = Maison.objects.filter(numero=numero)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Ce numéro de maison existe déjà.")
        return numero

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        nom = self.cleaned_data.get('nom')
        
        # Générer automatiquement si vide
        if not slug and nom:
            slug = slugify(nom)
        
        # Vérifier l'unicité
        if slug:
            qs = Maison.objects.filter(slug=slug)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                base_slug = slug
                counter = 1
                while Maison.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
        
        return slug

    def clean(self):
        cleaned_data = super().clean()
        capacite = cleaned_data.get('capacite_personnes')
        chambres = cleaned_data.get('nombre_chambres')
        
        # Validation : la capacité ne peut pas être inférieure au nombre de chambres
        if capacite and chambres and capacite < chambres:
            raise forms.ValidationError(
                "La capacité en personnes ne peut pas être inférieure au nombre de chambres."
            )
        
        return cleaned_data
    
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
        if user and not (hasattr(user, 'is_super_admin') and user.is_super_admin()):
            self.fields['maison'].queryset = Maison.objects.filter(gestionnaire=user)



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