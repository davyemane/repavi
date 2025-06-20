# users/forms.py - Version adaptée avec nouveaux rôles
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from .models import User, ProfilGestionnaire, ProfilClient

class CustomLoginForm(AuthenticationForm):
    """Formulaire de connexion personnalisé - ADAPTÉ"""
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Votre nom d\'utilisateur',
            'autocomplete': 'username'
        }),
        label='Nom d\'utilisateur'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Votre mot de passe',
            'autocomplete': 'current-password'
        }),
        label='Mot de passe'
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
        }),
        label='Se souvenir de moi'
    )


class CustomRegistrationForm(UserCreationForm):
    """Formulaire d'inscription personnalisé - ADAPTÉ AVEC NOUVEAUX RÔLES"""
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Nom d\'utilisateur'
        }),
        label='Nom d\'utilisateur'
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'votre.email@exemple.com'
        }),
        label='Email'
    )
    
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Prénom'
        }),
        label='Prénom'
    )
    
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Nom'
        }),
        label='Nom'
    )
    
    telephone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': '+33 1 23 45 67 89'
        }),
        label='Téléphone (optionnel)'
    )
    
    # ADAPTATION: nouveaux rôles
    role = forms.ChoiceField(
        choices=[
            ('CLIENT', 'Client - Je souhaite réserver des maisons'),
            ('GESTIONNAIRE', 'Gestionnaire - Je souhaite mettre mes maisons en location'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'text-indigo-600 focus:ring-indigo-500'
        }),
        label='Je suis un(e)',
        initial='CLIENT'
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Mot de passe'
        }),
        label='Mot de passe'
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Confirmer le mot de passe'
        }),
        label='Confirmer le mot de passe'
    )
    
    accepter_conditions = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
        }),
        label='J\'accepte les conditions d\'utilisation et la politique de confidentialité'
    )
    
    newsletter = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
        }),
        label='Je souhaite recevoir la newsletter',
        initial=True
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'telephone', 'role', 
                 'password1', 'password2', 'accepter_conditions', 'newsletter')
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Un compte avec cet email existe déjà.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.telephone = self.cleaned_data.get('telephone', '')
        user.role = self.cleaned_data['role']  # NOUVEAU
        user.newsletter = self.cleaned_data.get('newsletter', True)
        
        if commit:
            user.save()
            
            # Créer le profil étendu selon le nouveau rôle
            if user.role == 'GESTIONNAIRE':
                ProfilGestionnaire.objects.create(user=user)
            elif user.role == 'CLIENT':
                ProfilClient.objects.create(user=user)
        
        return user


class ProfileForm(forms.ModelForm):
    """Formulaire de modification du profil - ADAPTÉ"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'telephone', 'date_naissance',
                 'photo_profil', 'adresse', 'ville', 'code_postal', 'pays',
                 'newsletter', 'notifications_email', 'notifications_sms']
        
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'date_naissance': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'type': 'date'
            }),
            'photo_profil': forms.ClearableFileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'adresse': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'ville': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'code_postal': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'pays': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'newsletter': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'notifications_email': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'notifications_sms': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
        }


# NOUVEAU : Formulaire pour profil gestionnaire
class ProfilGestionnaireForm(forms.ModelForm):
    """Formulaire pour le profil étendu des gestionnaires"""
    
    class Meta:
        model = ProfilGestionnaire
        fields = ['siret', 'raison_sociale', 'iban', 'bic', 'piece_identite', 
                 'justificatif_domicile', 'kbis', 'auto_acceptation', 'delai_reponse_max']
        
        widgets = {
            'siret': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': '12345678901234'
            }),
            'raison_sociale': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Nom de votre société'
            }),
            'iban': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'FR76 XXXX XXXX XXXX XXXX XXXX XXX'
            }),
            'bic': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'BNPAFRPP'
            }),
            'piece_identite': forms.ClearableFileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'justificatif_domicile': forms.ClearableFileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'kbis': forms.ClearableFileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'auto_acceptation': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'delai_reponse_max': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'min': 1,
                'max': 168
            }),
        }


# NOUVEAU : Formulaire pour profil client
class ProfilClientForm(forms.ModelForm):
    """Formulaire pour le profil étendu des clients"""
    
    class Meta:
        model = ProfilClient
        fields = ['type_sejour_prefere', 'piece_identite', 'langue_preferee']
        
        widgets = {
            'type_sejour_prefere': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'piece_identite': forms.ClearableFileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'langue_preferee': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            }, choices=[
                ('fr', 'Français'),
                ('en', 'English'),
                ('es', 'Español'),
                ('de', 'Deutsch'),
                ('it', 'Italiano'),
            ]),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    """Formulaire de changement de mot de passe"""
    
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Mot de passe actuel'
        }),
        label='Mot de passe actuel'
    )
    
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Nouveau mot de passe'
        }),
        label='Nouveau mot de passe'
    )
    
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Confirmer le nouveau mot de passe'
        }),
        label='Confirmer le nouveau mot de passe'
    )


class PasswordResetRequestForm(forms.Form):
    """Formulaire de demande de réinitialisation de mot de passe"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Votre email'
        }),
        label='Email'
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("Aucun compte n'est associé à cet email.")
        return email


class PasswordResetForm(forms.Form):
    """Formulaire de réinitialisation de mot de passe"""
    
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Nouveau mot de passe'
        }),
        label='Nouveau mot de passe'
    )
    
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Confirmer le nouveau mot de passe'
        }),
        label='Confirmer le nouveau mot de passe'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("Les mots de passe ne correspondent pas.")
        
        return cleaned_data


# NOUVEAU : Formulaire de changement de rôle (Super Admin seulement)
class ChangeUserRoleForm(forms.ModelForm):
    """Formulaire pour changer le rôle d'un utilisateur (Super Admin)"""
    
    class Meta:
        model = User
        fields = ['role']
        widgets = {
            'role': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Seuls les super admins peuvent changer les rôles
        self.fields['role'].choices = User.ROLE_CHOICES