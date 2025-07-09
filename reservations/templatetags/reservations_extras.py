# reservations/templatetags/reservations_extras.py
# Filtres personnalisés pour les templates de réservations

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def get_statut_color(statut):
    """Retourne la classe de couleur CSS pour un statut de réservation"""
    colors = {
        'en_attente': 'orange',
        'confirmee': 'green',
        'terminee': 'blue',
        'annulee': 'red',
    }
    return colors.get(statut, 'gray')

@register.filter
def get_paiement_color(statut):
    """Retourne la classe de couleur CSS pour un statut de paiement"""
    colors = {
        'en_attente': 'orange',
        'valide': 'green',
        'echec': 'red',
        'rembourse': 'gray',
    }
    return colors.get(statut, 'gray')

@register.filter
def get_occupation_color(statut):
    """Retourne la classe de couleur CSS pour un statut d'occupation"""
    colors = {
        'libre': 'green',
        'occupe': 'blue',
        'maintenance': 'orange',
        'indisponible': 'red',
    }
    return colors.get(statut, 'gray')

@register.filter
def format_prix_fcfa(montant):
    """Formate un montant en FCFA avec séparateurs de milliers"""
    if montant is None:
        return "0 FCFA"
    try:
        return f"{int(montant):,} FCFA".replace(',', ' ')
    except (ValueError, TypeError):
        return f"{montant} FCFA"

@register.filter
def duree_en_texte(nombre_nuits):
    """Convertit un nombre de nuits en texte lisible"""
    if not nombre_nuits:
        return "0 nuit"
    
    if nombre_nuits == 1:
        return "1 nuit"
    elif nombre_nuits < 7:
        return f"{nombre_nuits} nuits"
    elif nombre_nuits < 30:
        semaines = nombre_nuits // 7
        jours_restants = nombre_nuits % 7
        if jours_restants == 0:
            return f"{semaines} semaine{'s' if semaines > 1 else ''}"
        else:
            return f"{semaines} semaine{'s' if semaines > 1 else ''} et {jours_restants} jour{'s' if jours_restants > 1 else ''}"
    else:
        mois = nombre_nuits // 30
        jours_restants = nombre_nuits % 30
        if jours_restants == 0:
            return f"{mois} mois"
        else:
            return f"{mois} mois et {jours_restants} jour{'s' if jours_restants > 1 else ''}"

@register.filter
def statut_badge(statut):
    """Retourne un badge HTML pour un statut"""
    colors = {
        'en_attente': ('orange', 'En attente'),
        'confirmee': ('green', 'Confirmée'),
        'terminee': ('blue', 'Terminée'),
        'annulee': ('red', 'Annulée'),
    }
    
    color, display = colors.get(statut, ('gray', statut.title()))
    
    html = f'''
    <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-{color}-100 text-{color}-700">
        {display}
    </span>
    '''
    return mark_safe(html)

@register.filter
def urgence_badge(jours):
    """Retourne un badge d'urgence selon le nombre de jours"""
    if jours == 0:
        color = "red"
        text = "Urgent"
        icon = "exclamation-triangle"
    elif jours <= 1:
        color = "orange"
        text = "Très urgent"
        icon = "clock"
    elif jours <= 3:
        color = "yellow"
        text = "Urgent"
        icon = "clock"
    else:
        color = "blue"
        text = f"Dans {jours} jours"
        icon = "calendar"
    
    html = f'''
    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-{color}-100 text-{color}-700">
        <i class="fas fa-{icon} mr-1"></i>
        {text}
    </span>
    '''
    return mark_safe(html)

@register.filter
def pourcentage_paiement(montant_paye, montant_total):
    """Calcule le pourcentage de paiement"""
    if not montant_total or montant_total == 0:
        return 0
    
    try:
        pourcentage = (float(montant_paye) / float(montant_total)) * 100
        return min(100, max(0, round(pourcentage, 1)))
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def progress_bar(pourcentage, color="blue"):
    """Génère une barre de progression"""
    html = f'''
    <div class="w-full bg-gray-200 rounded-full h-2">
        <div class="bg-{color}-600 h-2 rounded-full transition-all duration-300" style="width: {pourcentage}%"></div>
    </div>
    '''
    return mark_safe(html)

@register.filter
def montant_restant(prix_total, montant_paye):
    """Calcule le montant restant à payer"""
    try:
        total = float(prix_total) if prix_total else 0
        paye = float(montant_paye) if montant_paye else 0
        return max(0, total - paye)
    except (ValueError, TypeError):
        return 0

@register.filter
def jours_avant_echeance(date_echeance):
    """Calcule le nombre de jours avant une échéance"""
    from datetime import datetime, timezone
    
    if not date_echeance:
        return None
    
    # Convertir en date si c'est un datetime
    if hasattr(date_echeance, 'date'):
        date_echeance = date_echeance.date()
    
    today = datetime.now().date()
    delta = date_echeance - today
    return delta.days

@register.simple_tag
def statut_icon(statut):
    """Retourne l'icône appropriée pour un statut"""
    icons = {
        'en_attente': 'clock',
        'confirmee': 'check-circle',
        'terminee': 'flag-checkered',
        'annulee': 'times-circle',
        'valide': 'check',
        'echec': 'times',
        'rembourse': 'undo',
        'libre': 'home',
        'occupe': 'user',
        'maintenance': 'tools',
        'indisponible': 'ban',
    }
    return icons.get(statut, 'question-circle')

@register.simple_tag
def reservation_actions(reservation, user):
    """Génère les boutons d'action pour une réservation"""
    actions = []
    
    if not reservation.can_be_managed_by(user):
        return ""
    
    if reservation.statut == 'en_attente' and (user.is_gestionnaire() or user.is_super_admin()):
        actions.append(f'''
        <a href="/reservations/reservation/{reservation.numero}/gerer/" 
           class="inline-flex items-center px-3 py-1 bg-green-600 text-white text-xs font-medium rounded hover:bg-green-700">
            <i class="fas fa-check mr-1"></i> Confirmer
        </a>
        ''')
    
    if reservation.statut == 'confirmee' and reservation.montant_restant > 0:
        actions.append(f'''
        <a href="/reservations/reservation/{reservation.numero}/paiements/" 
           class="inline-flex items-center px-3 py-1 bg-blue-600 text-white text-xs font-medium rounded hover:bg-blue-700">
            <i class="fas fa-credit-card mr-1"></i> Paiements
        </a>
        ''')
    
    actions.append(f'''
    <a href="/reservations/reservation/{reservation.numero}/" 
       class="inline-flex items-center px-3 py-1 bg-gray-600 text-white text-xs font-medium rounded hover:bg-gray-700">
        <i class="fas fa-eye mr-1"></i> Voir
    </a>
    ''')
    
    return mark_safe(' '.join(actions))

@register.inclusion_tag('reservations/includes/statut_timeline.html')
def statut_timeline(reservation):
    """Affiche une timeline du statut de la réservation"""
    timeline = []
    
    # Étape 1: Création (toujours présente)
    timeline.append({
        'etape': 'creation',
        'nom': 'Réservation créée',
        'date': reservation.date_creation,
        'complete': True,
        'icon': 'plus-circle',
        'color': 'blue'
    })
    
    # Étape 2: Confirmation
    if reservation.statut in ['confirmee', 'terminee']:
        timeline.append({
            'etape': 'confirmation',
            'nom': 'Confirmée',
            'date': None,  # Vous pourriez ajouter une date de confirmation dans le modèle
            'complete': True,
            'icon': 'check-circle',
            'color': 'green'
        })
    elif reservation.statut == 'en_attente':
        timeline.append({
            'etape': 'confirmation',
            'nom': 'En attente de confirmation',
            'date': None,
            'complete': False,
            'icon': 'clock',
            'color': 'orange'
        })
    
    # Étape 3: Séjour / Annulation
    if reservation.statut == 'terminee':
        timeline.append({
            'etape': 'sejour',
            'nom': 'Séjour terminé',
            'date': reservation.date_fin,
            'complete': True,
            'icon': 'flag-checkered',
            'color': 'blue'
        })
    elif reservation.statut == 'annulee':
        timeline.append({
            'etape': 'annulation',
            'nom': 'Annulée',
            'date': reservation.date_annulation,
            'complete': True,
            'icon': 'times-circle',
            'color': 'red'
        })
    elif reservation.statut == 'confirmee':
        timeline.append({
            'etape': 'sejour',
            'nom': 'Séjour en cours',
            'date': reservation.date_debut,
            'complete': False,
            'icon': 'home',
            'color': 'green'
        })
    
    return {'timeline': timeline, 'reservation': reservation}