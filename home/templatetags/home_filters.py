# home/templatetags/home_filters.py

from django import template

register = template.Library()

@register.filter
def article(value):
    """
    Ajoute l'article français approprié devant un nom.
    
    Exemples:
    - ville -> la ville
    - maison -> la maison  
    - gestionnaire -> le gestionnaire
    - photo -> la photo
    - réservation -> la réservation
    - catégorie -> la catégorie
    """
    if not value:
        return ""
    
    value = str(value).lower().strip()
    
    # Mots féminins qui prennent "la"
    mots_feminins = [
        'ville', 'maison', 'photo', 'réservation', 'catégorie', 
        'image', 'facture', 'commande', 'demande', 'notification',
        'evaluation', 'chambre', 'cuisine', 'salle'
    ]
    
    # Mots masculins qui prennent "le"  
    mots_masculins = [
        'gestionnaire', 'client', 'utilisateur', 'admin', 'meuble',
        'paiement', 'contrat', 'document', 'rapport', 'compte'
    ]
    
    # Mots qui commencent par une voyelle ou h muet et prennent "l'"
    voyelles = ['a', 'e', 'i', 'o', 'u', 'h']
    
    # Vérifier si le mot commence par une voyelle
    if value and value[0] in voyelles:
        return f"l'{value}"
    
    # Vérifier dans les listes prédéfinies
    if value in mots_feminins:
        return f"la {value}"
    elif value in mots_masculins:
        return f"le {value}"
    
    # Règles par défaut basées sur les terminaisons françaises
    terminaisons_feminines = ['tion', 'sion', 'ance', 'ence', 'ure', 'ade', 'ée', 'ie', 'ette']
    terminaisons_masculines = ['ment', 'age', 'isme', 'eur', 'teur', 'ant']
    
    for terminaison in terminaisons_feminines:
        if value.endswith(terminaison):
            return f"la {value}"
    
    for terminaison in terminaisons_masculines:
        if value.endswith(terminaison):
            return f"le {value}"
    
    # Par défaut, utiliser "le" (la plupart des mots en français sont masculins par défaut)
    return f"le {value}"