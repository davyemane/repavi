# avis/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Avis, PhotoAvis, SignalementAvis
from home.models import Maison

class AvisForm(forms.ModelForm):
    """Formulaire pour créer/modifier un avis"""
    
    class Meta:
        model = Avis
        fields = [
            'note', 'titre', 'commentaire', 'date_sejour', 
            'duree_sejour', 'recommande'
        ]
        
        widgets = {
            'note': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
            }),
            'titre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'placeholder': 'Résumez votre expérience en quelques mots... (optionnel)'
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'rows': 4,
                'placeholder': 'Partagez votre expérience détaillée... (optionnel)'
            }),
            'date_sejour': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
            }),
            'duree_sejour': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'min': 1,
                'placeholder': 'Nombre de nuits (optionnel)'
            }),
            'recommande': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }
        
        labels = {
            'note': 'Votre note *',
            'titre': 'Titre de votre avis',
            'commentaire': 'Votre commentaire détaillé',
            'date_sejour': 'Date de votre séjour',
            'duree_sejour': 'Durée du séjour (nuits)',
            'recommande': 'Je recommande cette maison'
        }
        
        help_texts = {
            'note': 'Donnez une note de 1 à 5 étoiles selon votre expérience (obligatoire)',
            'titre': 'Un titre accrocheur qui résume votre avis (optionnel)',
            'commentaire': 'Décrivez votre expérience pour aider les autres voyageurs (optionnel)',
            'date_sejour': 'Quand avez-vous séjourné dans cette maison ? (optionnel)',
            'duree_sejour': 'Combien de nuits avez-vous passées ? (optionnel)'
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.maison = kwargs.pop('maison', None)
        super().__init__(*args, **kwargs)
        
        # Rendre les champs facultatifs (sauf note)
        self.fields['titre'].required = False
        self.fields['commentaire'].required = False
        self.fields['date_sejour'].required = False
        self.fields['duree_sejour'].required = False
        self.fields['recommande'].required = False
        
        # Seule la note est obligatoire
        self.fields['note'].required = True
        
        # Personnaliser les choix de notes avec des étoiles
        self.fields['note'].choices = [
            ('', 'Choisissez votre note *'),
            (5, '★★★★★ Excellent'),
            (4, '★★★★☆ Très bien'),
            (3, '★★★☆☆ Bien'),
            (2, '★★☆☆☆ Décevant'),
            (1, '★☆☆☆☆ Très décevant'),
        ]
        
        # Validation pour les nouveaux avis seulement
        if self.user and self.maison and not self.instance.pk:
            if Avis.objects.filter(client=self.user, maison=self.maison).exists():
                raise ValidationError("Vous avez déjà donné un avis pour cette maison.")
    
    def clean_commentaire(self):
        """Validation du commentaire (optionnel)"""
        commentaire = self.cleaned_data.get('commentaire', '')
        
        # Si commentaire fourni, vérifier la longueur
        if commentaire:
            if len(commentaire) < 5:
                raise ValidationError("Si vous ajoutez un commentaire, il doit contenir au moins 5 caractères.")
            
            if len(commentaire) > 2000:
                raise ValidationError("Votre commentaire ne peut pas dépasser 2000 caractères.")
        
        return commentaire
    
    def clean_titre(self):
        """Validation du titre (optionnel)"""
        titre = self.cleaned_data.get('titre', '')
        
        if titre and len(titre) > 100:
            raise ValidationError("Le titre ne peut pas dépasser 100 caractères.")
        
        return titre
    
    def clean_date_sejour(self):
        """Validation de la date de séjour (optionnel)"""
        date_sejour = self.cleaned_data.get('date_sejour')
        
        if date_sejour:
            from django.utils import timezone
            from datetime import timedelta
            
            # Ne peut pas être dans le futur
            if date_sejour > timezone.now().date():
                raise ValidationError("La date de séjour ne peut pas être dans le futur.")
            
            # Ne peut pas être trop ancienne (ex: plus de 2 ans)
            date_limite = timezone.now().date() - timedelta(days=730)
            if date_sejour < date_limite:
                raise ValidationError("La date de séjour ne peut pas être antérieure à 2 ans.")
        
        return date_sejour
    
    def clean_duree_sejour(self):
        """Validation de la durée de séjour (optionnel)"""
        duree = self.cleaned_data.get('duree_sejour')
        
        if duree is not None:
            if duree < 1:
                raise ValidationError("La durée doit être d'au moins 1 nuit.")
            if duree > 365:
                raise ValidationError("La durée ne peut pas dépasser 365 nuits.")
        
        return duree
    
    def clean_note(self):
        """Validation de la note (obligatoire)"""
        note = self.cleaned_data.get('note')
        
        if not note:
            raise ValidationError("La note est obligatoire.")
        
        if note not in [1, 2, 3, 4, 5]:
            raise ValidationError("La note doit être entre 1 et 5.")
        
        return note


class PhotoAvisForm(forms.ModelForm):
    """Formulaire pour ajouter des photos à un avis"""
    
    class Meta:
        model = PhotoAvis
        fields = ['image', 'legende']
        
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
                'accept': 'image/*'
            }),
            'legende': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'placeholder': 'Description de la photo (optionnel)'
            })
        }
        
        labels = {
            'image': 'Photo',
            'legende': 'Légende'
        }
    
    def clean_image(self):
        """Validation de l'image"""
        image = self.cleaned_data.get('image')
        
        if image:
            # Vérifier la taille du fichier (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("L'image ne peut pas dépasser 5 MB.")
            
            # Vérifier le format
            valid_formats = ['JPEG', 'JPG', 'PNG', 'WEBP']
            if hasattr(image, 'content_type'):
                if not any(fmt.lower() in image.content_type.lower() for fmt in valid_formats):
                    raise ValidationError("Format d'image non supporté. Utilisez JPEG, PNG ou WEBP.")
        
        return image


# TEMPORAIREMENT DÉSACTIVÉ - Upload multiple de photos
# Cette fonctionnalité sera implémentée plus tard si nécessaire
# 
# class MultiplePhotoAvisForm(forms.Form):
#     """Formulaire pour uploader plusieurs photos en une fois - EN DÉVELOPPEMENT"""
#     pass


class ReponseGestionnaireForm(forms.ModelForm):
    """Formulaire pour les réponses des gestionnaires aux avis"""
    
    class Meta:
        model = Avis
        fields = ['reponse_gestionnaire']
        
        widgets = {
            'reponse_gestionnaire': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'rows': 4,
                'placeholder': 'Répondez de manière professionnelle et constructive...'
            })
        }
        
        labels = {
            'reponse_gestionnaire': 'Votre réponse publique'
        }
        
        help_texts = {
            'reponse_gestionnaire': 'Cette réponse sera visible par tous les visiteurs'
        }
    
    def __init__(self, *args, **kwargs):
        self.gestionnaire = kwargs.pop('gestionnaire', None)
        super().__init__(*args, **kwargs)
    
    def clean_reponse_gestionnaire(self):
        """Validation de la réponse"""
        reponse = self.cleaned_data.get('reponse_gestionnaire')
        
        if reponse:
            if len(reponse) < 10:
                raise ValidationError("Votre réponse doit contenir au moins 10 caractères.")
            
            if len(reponse) > 1000:
                raise ValidationError("Votre réponse ne peut pas dépasser 1000 caractères.")
        
        return reponse
    
    def save(self, commit=True):
        """Sauvegarder avec les informations du gestionnaire"""
        avis = super().save(commit=False)
        
        if self.gestionnaire:
            avis.reponse_par = self.gestionnaire
            from django.utils import timezone
            avis.date_reponse = timezone.now()
        
        if commit:
            avis.save()
        return avis


class SignalementAvisForm(forms.ModelForm):
    """Formulaire pour signaler un avis"""
    
    class Meta:
        model = SignalementAvis
        fields = ['raison', 'commentaire']
        
        widgets = {
            'raison': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-colors'
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-colors',
                'rows': 3,
                'placeholder': 'Expliquez pourquoi vous signalez cet avis...'
            })
        }
        
        labels = {
            'raison': 'Raison du signalement',
            'commentaire': 'Détails (optionnel)'
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.avis = kwargs.pop('avis', None)
        super().__init__(*args, **kwargs)
    
    def clean_commentaire(self):
        """Validation du commentaire de signalement"""
        commentaire = self.cleaned_data.get('commentaire')
        
        if commentaire and len(commentaire) > 500:
            raise ValidationError("Le commentaire ne peut pas dépasser 500 caractères.")
        
        return commentaire
    
    def save(self, commit=True):
        """Sauvegarder avec les informations du signalement"""
        signalement = super().save(commit=False)
        
        if self.user:
            signalement.user = self.user
        if self.avis:
            signalement.avis = self.avis
        
        if commit:
            signalement.save()
        return signalement


class FiltreAvisForm(forms.Form):
    """Formulaire pour filtrer les avis"""
    
    note_min = forms.ChoiceField(
        choices=[
            ('', 'Toutes les notes'),
            ('1', '1 étoile et plus'),
            ('2', '2 étoiles et plus'),
            ('3', '3 étoiles et plus'),
            ('4', '4 étoiles et plus'),
            ('5', '5 étoiles uniquement'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
        }),
        label='Note minimum'
    )
    
    avec_photos = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        }),
        label='Avec photos uniquement'
    )
    
    avec_reponse = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        }),
        label='Avec réponse du gestionnaire'
    )
    
    tri = forms.ChoiceField(
        choices=[
            ('-date_creation', 'Plus récents'),
            ('date_creation', 'Plus anciens'),
            ('-note', 'Meilleures notes'),
            ('note', 'Notes les plus basses'),
            ('-nombre_likes', 'Plus utiles'),
        ],
        initial='-date_creation',
        widget=forms.Select(attrs={
            'class': 'px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
        }),
        label='Trier par'
    )


class ModerationAvisForm(forms.ModelForm):
    """Formulaire pour la modération des avis (admin/gestionnaire)"""
    
    class Meta:
        model = Avis
        fields = ['statut_moderation', 'raison_rejet']
        
        widgets = {
            'statut_moderation': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
            }),
            'raison_rejet': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'rows': 3,
                'placeholder': 'Expliquez la raison du rejet si nécessaire...'
            })
        }
        
        labels = {
            'statut_moderation': 'Décision de modération',
            'raison_rejet': 'Raison du rejet'
        }
    
    def __init__(self, *args, **kwargs):
        self.moderateur = kwargs.pop('moderateur', None)
        super().__init__(*args, **kwargs)
        
        # Masquer raison_rejet si pas de rejet
        if self.instance and self.instance.statut_moderation != 'rejete':
            self.fields['raison_rejet'].widget = forms.HiddenInput()
    
    def clean(self):
        """Validation croisée"""
        cleaned_data = super().clean()
        statut = cleaned_data.get('statut_moderation')
        raison_rejet = cleaned_data.get('raison_rejet')
        
        # Si rejet, une raison est obligatoire
        if statut == 'rejete' and not raison_rejet:
            raise ValidationError("Une raison de rejet est obligatoire.")
        
        return cleaned_data
    
    def save(self, commit=True):
        """Sauvegarder avec les informations de modération"""
        avis = super().save(commit=False)
        
        if self.moderateur:
            avis.modere_par = self.moderateur
            from django.utils import timezone
            avis.date_moderation = timezone.now()
        
        if commit:
            avis.save()
        return avis


# Formset pour les photos multiples
PhotoAvisFormSet = forms.inlineformset_factory(
    Avis,
    PhotoAvis,
    form=PhotoAvisForm,
    extra=3,
    max_num=5,
    can_delete=True,
    widgets={
        'DELETE': forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded'
        })
    }
)