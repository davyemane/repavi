# ==========================================
# apps/clients/forms.py - Fiche client simple
# ==========================================
from django import forms
from .models import Client

class ClientForm(forms.ModelForm):
    """
    Fiche client simple selon cahier des charges
    Tous les champs requis par le cahier
    """
    
    class Meta:
        model = Client
        fields = [
            'nom', 'prenom', 'telephone', 'email',
            'piece_identite', 'adresse_residence',
            'contact_urgence_nom', 'contact_urgence_tel'
        ]
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'placeholder': 'Nom de famille'
            }),
            'prenom': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'placeholder': 'Prénom'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'placeholder': '+237 XXX XXX XXX'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'placeholder': 'email@exemple.com'
            }),
            'piece_identite': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600',
                'accept': 'image/*'
            }),
            'adresse_residence': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'rows': 3,
                'placeholder': 'Adresse de résidence habituelle'
            }),
            'contact_urgence_nom': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'placeholder': 'Nom du contact d\'urgence'
            }),
            'contact_urgence_tel': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100',
                'placeholder': 'Téléphone du contact d\'urgence'
            }),
        }
        labels = {
            'nom': 'Nom de famille',
            'prenom': 'Prénom',
            'telephone': 'Numéro de téléphone',
            'email': 'Adresse email',
            'piece_identite': 'Pièce d\'identité (photo)',
            'adresse_residence': 'Adresse de résidence',
            'contact_urgence_nom': 'Contact d\'urgence - Nom',
            'contact_urgence_tel': 'Contact d\'urgence - Téléphone',
        }
        help_texts = {
            'piece_identite': 'Photo de la carte d\'identité ou passeport',
            'contact_urgence_nom': 'Personne à contacter en cas d\'urgence',
        }
