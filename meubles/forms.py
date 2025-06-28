from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from home.models import Maison
from .models import TypeMeuble, Meuble, InventaireMaison, PhotoMeuble

User = get_user_model()


class TypeMeubleForm(forms.ModelForm):
    """Formulaire pour les types de meubles"""
    
    class Meta:
        model = TypeMeuble
        fields = ['nom', 'description', 'categorie', 'icone']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Nom du type de meuble'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 3,
                'placeholder': 'Description du type de meuble...'
            }),
            'categorie': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'icone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Nom de l\'icône (ex: bed, chair, table)'
            }),
        }


class MeubleForm(forms.ModelForm):
    """Formulaire pour les meubles"""
    
    class Meta:
        model = Meuble
        fields = [
            'nom', 'type_meuble', 'numero_serie', 'maison', 'etat',
            'date_entree', 'piece', 'marque', 'modele', 'couleur',
            'materiaux', 'dimensions', 'prix_achat', 'valeur_actuelle', 'notes'
        ]
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Nom du meuble'
            }),
            'type_meuble': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'numero_serie': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Numéro de série unique'
            }),
            'maison': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'etat': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'date_entree': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'type': 'date'
            }),
            'piece': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'marque': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Marque du meuble'
            }),
            'modele': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Modèle'
            }),
            'couleur': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Couleur principale'
            }),
            'materiaux': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Matériaux (bois, métal, etc.)'
            }),
            'dimensions': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'L x P x H en cm'
            }),
            'prix_achat': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Prix d\'achat en FCFA',
                'step': '0.01'
            }),
            'valeur_actuelle': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Valeur actuelle en FCFA',
                'step': '0.01'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 4,
                'placeholder': 'Notes et observations...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrer les maisons selon les permissions
        if self.user:
            if hasattr(self.user, 'is_super_admin') and self.user.is_super_admin():
                self.fields['maison'].queryset = Maison.objects.all()
            else:
                self.fields['maison'].queryset = Maison.objects.filter(gestionnaire=self.user)
        
        # Auto-générer le numéro de série si nouveau meuble
        if not self.instance.pk and self.user:
            maison_id = self.data.get('maison') if self.data else None
            if maison_id:
                try:
                    maison = Maison.objects.get(id=maison_id)
                    # Compter les meubles existants pour cette maison
                    count = maison.meubles.count() + 1
                    self.fields['numero_serie'].initial = f"{maison.numero}-M{count:03d}"
                except Maison.DoesNotExist:
                    pass
    
    def clean_numero_serie(self):
        numero_serie = self.cleaned_data.get('numero_serie')
        
        # Vérifier l'unicité
        qs = Meuble.objects.filter(numero_serie=numero_serie)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise ValidationError("Ce numéro de série existe déjà.")
        
        return numero_serie
    
    def clean(self):
        cleaned_data = super().clean()
        prix_achat = cleaned_data.get('prix_achat')
        valeur_actuelle = cleaned_data.get('valeur_actuelle')
        
        # La valeur actuelle ne peut pas être supérieure au prix d'achat
        if prix_achat and valeur_actuelle and valeur_actuelle > prix_achat:
            raise ValidationError("La valeur actuelle ne peut pas être supérieure au prix d'achat.")
        
        return cleaned_data


class MeubleFilterForm(forms.Form):
    """Formulaire de filtrage des meubles"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Rechercher un meuble...'
        })
    )
    
    maison = forms.ModelChoiceField(
        queryset=Maison.objects.all(),
        required=False,
        empty_label="Toutes les maisons",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    
    type_meuble = forms.ModelChoiceField(
        queryset=TypeMeuble.objects.all(),
        required=False,
        empty_label="Tous les types",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    
    etat = forms.ChoiceField(
        choices=[('', 'Tous les états')] + Meuble.ETAT_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    
    piece = forms.ChoiceField(
        choices=[('', 'Toutes les pièces')] + [
            ('salon', 'Salon'),
            ('chambre_1', 'Chambre 1'),
            ('chambre_2', 'Chambre 2'),
            ('chambre_3', 'Chambre 3'),
            ('cuisine', 'Cuisine'),
            ('salle_bain', 'Salle de bain'),
            ('terrasse', 'Terrasse'),
            ('balcon', 'Balcon'),
            ('garage', 'Garage'),
            ('autre', 'Autre'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    
    verification_requise = forms.BooleanField(
        required=False,
        label="Nécessite vérification",
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrer les maisons selon les permissions
        if user:
            if hasattr(user, 'is_super_admin') and user.is_super_admin():
                self.fields['maison'].queryset = Maison.objects.all().order_by('nom')
            else:
                self.fields['maison'].queryset = Maison.objects.filter(gestionnaire=user).order_by('nom')


class InventaireForm(forms.ModelForm):
    """Formulaire pour créer un inventaire"""
    
    class Meta:
        model = InventaireMaison
        fields = ['maison', 'type_inventaire', 'observations']
        widgets = {
            'maison': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'type_inventaire': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'observations': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'rows': 4,
                'placeholder': 'Observations générales sur l\'inventaire...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrer les maisons selon les permissions
        if self.user:
            if hasattr(self.user, 'is_super_admin') and self.user.is_super_admin():
                self.fields['maison'].queryset = Maison.objects.all().order_by('nom')
            else:
                self.fields['maison'].queryset = Maison.objects.filter(gestionnaire=self.user).order_by('nom')


class PhotoMeubleForm(forms.ModelForm):
    """Formulaire pour ajouter une photo à un meuble"""
    
    class Meta:
        model = PhotoMeuble
        fields = ['image', 'titre', 'type_photo']
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'accept': 'image/*'
            }),
            'titre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Titre de la photo'
            }),
            'type_photo': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
        }


class MeubleEtatForm(forms.Form):
    """Formulaire rapide pour changer l'état d'un meuble"""
    
    etat = forms.ChoiceField(
        choices=Meuble.ETAT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    
    motif = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'rows': 3,
            'placeholder': 'Motif du changement d\'état (optionnel)...'
        })
    )
    
    cout = forms.DecimalField(
        required=False,
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Coût éventuel (réparation, etc.)',
            'step': '0.01'
        })
    )


class MeubleImportForm(forms.Form):
    """Formulaire pour importer des meubles en masse"""
    
    maison = forms.ModelChoiceField(
        queryset=Maison.objects.all(),
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        }),
        help_text="Maison pour laquelle importer les meubles"
    )
    
    fichier_csv = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'accept': '.csv'
        }),
        help_text="Fichier CSV avec les colonnes : nom, type_meuble, piece, etat, marque, modele"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrer les maisons selon les permissions
        if self.user:
            if hasattr(self.user, 'is_super_admin') and self.user.is_super_admin():
                self.fields['maison'].queryset = Maison.objects.all().order_by('nom')
            else:
                self.fields['maison'].queryset = Maison.objects.filter(gestionnaire=self.user).order_by('nom')
    
    def clean_fichier_csv(self):
        fichier = self.cleaned_data.get('fichier_csv')
        
        if fichier:
            # Vérifier l'extension
            if not fichier.name.endswith('.csv'):
                raise ValidationError("Le fichier doit être au format CSV.")
            
            # Vérifier la taille (max 5MB)
            if fichier.size > 5 * 1024 * 1024:
                raise ValidationError("Le fichier ne doit pas dépasser 5MB.")
        
        return fichier


class RapportMeublesForm(forms.Form):
    """Formulaire pour générer des rapports sur les meubles"""
    
    TYPE_RAPPORT_CHOICES = [
        ('inventaire', 'Inventaire complet'),
        ('defectueux', 'Meubles défectueux'),
        ('verification', 'Meubles à vérifier'),
        ('valeur', 'Évaluation financière'),
        ('historique', 'Historique des états'),
    ]
    
    type_rapport = forms.ChoiceField(
        choices=TYPE_RAPPORT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    
    maison = forms.ModelChoiceField(
        queryset=Maison.objects.all(),
        required=False,
        empty_label="Toutes les maisons",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    
    date_debut = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'type': 'date'
        }),
        help_text="Pour les rapports avec plage de dates"
    )
    
    date_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'type': 'date'
        }),
        help_text="Pour les rapports avec plage de dates"
    )
    
    format_export = forms.ChoiceField(
        choices=[
            ('html', 'Aperçu HTML'),
            ('pdf', 'Téléchargement PDF'),
            ('excel', 'Export Excel'),
        ],
        initial='html',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrer les maisons selon les permissions
        if self.user:
            if hasattr(self.user, 'is_super_admin') and self.user.is_super_admin():
                self.fields['maison'].queryset = Maison.objects.all().order_by('nom')
            else:
                self.fields['maison'].queryset = Maison.objects.filter(gestionnaire=self.user).order_by('nom')
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_debut and date_fin and date_debut > date_fin:
            raise ValidationError("La date de début doit être antérieure à la date de fin.")
        
        return cleaned_data