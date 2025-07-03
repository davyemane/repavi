# avis/views.py
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from .models import Avis
from .forms import AvisForm
from home.models import Maison

@login_required
@require_POST
def creer_avis(request, maison_slug):
    """Créer un nouvel avis via AJAX"""
    maison = get_object_or_404(Maison, slug=maison_slug)
    
    # Vérifier que l'utilisateur est un client
    if not hasattr(request.user, 'is_client') or not request.user.is_client():
        return JsonResponse({
            'success': False,
            'error': 'Seuls les clients peuvent donner des avis.'
        })
    
    form = AvisForm(request.POST)
    if form.is_valid():
        avis = form.save(commit=False)
        avis.user = request.user
        avis.maison = maison
        avis.save()
        
        # Retourner les nouvelles statistiques
        return JsonResponse({
            'success': True,
            'message': 'Votre avis a été publié avec succès !',
            'note_moyenne': maison.get_note_moyenne(),
            'nombre_avis': maison.get_nombre_avis(),
        })
    
    return JsonResponse({
        'success': False,
        'errors': form.errors
    })

def get_avis_list(request, maison_slug):
    """Récupérer la liste des avis paginée via AJAX"""
    maison = get_object_or_404(Maison, slug=maison_slug)
    page_number = request.GET.get('page', 1)
    
    avis_list = maison.avis.all()
    paginator = Paginator(avis_list, 5)  # 5 avis par page
    page_obj = paginator.get_page(page_number)
    
    avis_html = render_to_string('avis/avis_list.html', {
        'avis_list': page_obj,
        'page_obj': page_obj,
    })
    
    return JsonResponse({
        'avis_html': avis_html,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
    })