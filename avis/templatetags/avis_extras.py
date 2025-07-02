# avis/templatetags/avis_extras.py
from django import template

register = template.Library()

@register.filter
def get_note_moyenne(maison):
    """Récupère la note moyenne d'une maison de manière sécurisée"""
    try:
        if hasattr(maison, '_note_moyenne'):
            return maison._note_moyenne
        elif hasattr(maison, 'get_note_moyenne'):
            return maison.get_note_moyenne()
        else:
            return 0
    except:
        return 0

@register.filter
def get_nombre_avis(maison):
    """Récupère le nombre d'avis d'une maison de manière sécurisée"""
    try:
        if hasattr(maison, '_nombre_avis'):
            return maison._nombre_avis
        elif hasattr(maison, 'get_nombre_avis'):
            return maison.get_nombre_avis()
        else:
            return 0
    except:
        return 0

@register.inclusion_tag('stars_display.html')
def display_stars(note, show_number=True):
    """Affiche les étoiles pour une note donnée"""
    note = float(note) if note else 0
    full_stars = int(note)
    half_star = (note - full_stars) >= 0.5
    empty_stars = 5 - full_stars - (1 if half_star else 0)
    
    return {
        'note': note,
        'full_stars': range(full_stars),
        'half_star': half_star,
        'empty_stars': range(empty_stars),
        'show_number': show_number,
    }

