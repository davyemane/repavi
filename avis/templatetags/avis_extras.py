# avis/templatetags/avis_extras.py - Version complète avec template tag pour étoiles

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

@register.inclusion_tag('avis/stars_display.html')
def display_stars(note, show_number=False, size='normal', show_count=False, count=0):
    """
    Affiche les étoiles pour une note donnée
    
    Usage:
    {% display_stars maison.get_note_moyenne %}
    {% display_stars note show_number=True %}
    {% display_stars note size='large' show_number=True %}
    {% display_stars note show_count=True count=maison.get_nombre_avis %}
    """
    try:
        note = float(note) if note else 0
    except (ValueError, TypeError):
        note = 0
        
    full_stars = int(note)
    half_star = (note - full_stars) >= 0.5
    empty_stars = 5 - full_stars - (1 if half_star else 0)
    
    return {
        'note': note,
        'full_stars': range(full_stars),
        'half_star': half_star,
        'empty_stars': range(empty_stars),
        'show_number': show_number,
        'show_count': show_count,
        'count': count,
        'size': size,
    }

@register.simple_tag
def stars_html(note, size='normal', show_number=False):
    """
    Génère le HTML des étoiles directement
    
    Usage:
    {% stars_html maison.get_note_moyenne %}
    {% stars_html note size='large' show_number=True %}
    """
    try:
        note = float(note) if note else 0
    except (ValueError, TypeError):
        note = 0
        
    full_stars = int(note)
    half_star = (note - full_stars) >= 0.5
    empty_stars = 5 - full_stars - (1 if half_star else 0)
    
    # Classes CSS selon la taille
    size_class = {
        'small': 'text-sm',
        'normal': '',
        'large': 'text-lg'
    }.get(size, '')
    
    html = ['<div class="flex items-center space-x-1">']
    
    # Étoiles pleines
    for _ in range(full_stars):
        html.append(f'<i class="fas fa-star text-yellow-400 {size_class}"></i>')
    
    # Demi-étoile
    if half_star:
        html.append(f'<i class="fas fa-star-half-alt text-yellow-400 {size_class}"></i>')
    
    # Étoiles vides
    for _ in range(empty_stars):
        html.append(f'<i class="far fa-star text-gray-300 {size_class}"></i>')
    
    # Note numérique
    if show_number and note > 0:
        number_class = 'text-lg font-semibold' if size == 'large' else 'font-medium'
        html.append(f'<span class="ml-2 {number_class} text-gray-700">{note}</span>')
    
    html.append('</div>')
    
    return ''.join(html)

@register.filter
def can_be_managed_by(maison, user):
    """Check if a maison can be managed by the given user"""
    if hasattr(maison, 'can_be_managed_by'):
        return maison.can_be_managed_by(user)
    return False

@register.filter
def stars_range(note):
    """Retourne une liste pour les boucles d'étoiles"""
    try:
        note = int(float(note)) if note else 0
        return range(min(5, max(0, note)))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def empty_stars_range(note):
    """Retourne une liste pour les étoiles vides"""
    try:
        note = int(float(note)) if note else 0
        filled = min(5, max(0, note))
        return range(5 - filled)
    except (ValueError, TypeError):
        return range(5)

