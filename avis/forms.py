# avis/forms.py
from django import forms
from .models import Avis

class AvisForm(forms.ModelForm):
    class Meta:
        model = Avis
        fields = ['note', 'commentaire']
        widgets = {
            'note': forms.RadioSelect(choices=[
                (1, '1 étoile'),
                (2, '2 étoiles'),
                (3, '3 étoiles'),
                (4, '4 étoiles'),
                (5, '5 étoiles'),
            ], attrs={'class': 'note-radio'}),
            'commentaire': forms.Textarea(attrs={
                'placeholder': 'Partagez votre expérience...',
                'rows': 4,
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            })
        }
        labels = {
            'note': 'Votre note',
            'commentaire': 'Votre commentaire'
        }
    
    def clean_commentaire(self):
        commentaire = self.cleaned_data.get('commentaire')
        if len(commentaire.strip()) < 10:
            raise forms.ValidationError("Le commentaire doit contenir au moins 10 caractères.")
        return commentaire