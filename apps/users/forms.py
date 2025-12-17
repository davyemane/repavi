# ==========================================
# apps/users/forms.py - Gestion utilisateurs (Super Admin uniquement)
# ==========================================
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from django.forms import ValidationError

class GestionnaireCreationForm(UserCreationForm):
    """
    Formulaire création gestionnaire pour Super Admin
    Selon cahier : seuls Super Admin peuvent créer/supprimer gestionnaires
    """
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'telephone', 'profil']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'profil': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Par défaut : gestionnaire
        self.fields['profil'].initial = 'gestionnaire'
        
        # Styles pour les champs password
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
        })


class ReceptionnisteCreationForm(UserCreationForm):
    """
    Formulaire création réceptionniste pour Super Admin
    Seuls Super Admin peuvent créer des réceptionnistes
    """

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'telephone']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Styles pour les champs password
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        # Forcer le profil à réceptionniste
        user.profil = 'receptionniste'
        if commit:
            user.save()
        return user


#profil_utilisateur
class ProfilUtilisateurForm(forms.ModelForm):
    """
    Formulaire profil utilisateur selon cahier
    """
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'telephone', 'email', 'profil']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }),
            'profil': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
            }), 
        }
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'telephone': 'Téléphone',
            'email': 'Email',
            'profil': 'Profil',
        }
        help_texts = {
            'first_name': 'Prénom du gestionnaire',
            'last_name': 'Nom du gestionnaire',
            'telephone': 'Téléphone du gestionnaire',
            'email': 'Email du gestionnaire',
            'profil': 'Profil du gestionnaire',
        }
        error_messages = {
            'email': {
                'invalid': 'Adresse email invalide. Veuillez entrer une adresse valide.',
            },
        }
        # Validation personnalisée pour le téléphone
        def clean_telephone(self):
            telephone = self.cleaned_data.get('telephone')
            if not telephone.isdigit() or len(telephone) < 8:
                raise ValidationError('Le téléphone doit contenir au moins 8 chiffres.')
            return telephone
        def clean_email(self):
            email = self.cleaned_data.get('email')
            if not email:
                raise ValidationError('L\'email est requis.')
            if '@' not in email or '.' not in email.split('@')[-1]:
                raise ValidationError('Veuillez entrer une adresse email valide.')
            return email
        def clean_profil(self):
            profil = self.cleaned_data.get('profil')
            if profil not in ['super_admin', 'gestionnaire']:
                raise ValidationError('Profil invalide. Choisissez entre Super Admin ou Gestionnaire.')
            return profil   
        def clean(self):
            cleaned_data = super().clean()
            first_name = cleaned_data.get('first_name')
            last_name = cleaned_data.get('last_name')
            if not first_name or not last_name:
                raise ValidationError('Le prénom et le nom sont requis.')
            return cleaned_data
        def clean_password(self):
            password = self.cleaned_data.get('password')
            if not password:
                raise ValidationError('Le mot de passe est requis.')
            return password
        def clean_password2(self):
            password1 = self.cleaned_data.get('password1')
            password2 = self.cleaned_data.get('password2')
            if password1 and password2 and password1 != password2:
                raise ValidationError('Les mots de passe ne correspondent pas.')
            return password2
        def clean_username(self):
            username = self.cleaned_data.get('username')
            if not username:
                raise ValidationError('Le nom d\'utilisateur est requis.')
            if User.objects.filter(username=username).exists():
                raise ValidationError('Ce nom d\'utilisateur est déjà pris. Veuillez en choisir un autre.')
            return username
        

# ==========================================
# Formulaire de recherche global
# ==========================================
class RechercheGlobaleForm(forms.Form):
    """
    Formulaire de recherche globale dans tout le système
    """
    CATEGORIES = [
        ('tous', 'Tout rechercher'),
        ('appartements', 'Appartements'),
        ('clients', 'Clients'),
        ('reservations', 'Réservations'),
    ]
    
    q = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 pl-12 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
            'placeholder': 'Rechercher...'
        }),
        label='',
        required=False
    )
    
    categorie = forms.ChoiceField(
        choices=CATEGORIES,
        widget=forms.Select(attrs={
            'class': 'px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600'
        }),
        required=False,
        initial='tous'
    )