# avis/views.py - Version avec messages Flash
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from .models import Avis
from .forms import AvisForm
from home.models import Maison

@login_required
@require_POST
def creer_avis(request, maison_slug):
    """Créer un nouvel avis avec messages Flash et redirection"""
    try:
        maison = get_object_or_404(Maison, slug=maison_slug)
        
        # Vérifier que l'utilisateur est un client
        if hasattr(request.user, 'is_client'):
            if callable(request.user.is_client):
                is_client = request.user.is_client()
            else:
                is_client = request.user.is_client
        else:
            # Si pas de méthode is_client, considérer comme client par défaut
            is_client = True
            
        if not is_client:
            messages.error(request, 'Seuls les clients peuvent donner des avis.')
            return redirect('home:maison_detail', slug=maison_slug)
        
        # Vérifier si l'utilisateur a déjà donné un avis pour cette maison
        existing_avis = Avis.objects.filter(user=request.user, maison=maison).first()
        if existing_avis:
            messages.warning(request, 'Vous avez déjà donné un avis pour cette maison.')
            return redirect('home:maison_detail', slug=maison_slug)
        
        form = AvisForm(request.POST)
        if form.is_valid():
            avis = form.save(commit=False)
            avis.user = request.user
            avis.maison = maison
            avis.save()
            
            messages.success(request, f'Votre avis a été publié avec succès ! Merci pour votre note de {avis.note} étoile{"s" if avis.note > 1 else ""}.')
            return redirect('home:maison_detail', slug=maison_slug)
        else:
            # Afficher les erreurs du formulaire
            for field, errors in form.errors.items():
                for error in errors:
                    if field == 'note':
                        messages.error(request, f'Note : {error}')
                    elif field == 'commentaire':
                        messages.error(request, f'Commentaire : {error}')
                    else:
                        messages.error(request, f'{field} : {error}')
            return redirect('home:maison_detail', slug=maison_slug)
    
    except Exception as e:
        print(f"Erreur lors de la création de l'avis: {e}")
        messages.error(request, 'Une erreur est survenue lors de la publication de votre avis. Veuillez réessayer.')
        return redirect('home:maison_detail', slug=maison_slug)

def get_avis_list(request, maison_slug):
    """Récupérer la liste des avis paginée - conservé pour la pagination AJAX si nécessaire"""
    from django.http import JsonResponse
    from django.core.paginator import Paginator
    from django.template.loader import render_to_string
    
    try:
        maison = get_object_or_404(Maison, slug=maison_slug)
        page_number = request.GET.get('page', 1)
        
        avis_list = Avis.objects.filter(maison=maison).order_by('-date_creation')
        paginator = Paginator(avis_list, 5)
        page_obj = paginator.get_page(page_number)
        
        # Template simplifié
        avis_html = '<div class="space-y-6">'
        for avis in page_obj:
            stars = '★' * avis.note + '☆' * (5 - avis.note)
            avis_html += f'''
            <div class="border-b border-gray-100 pb-6 last:border-b-0 last:pb-0">
                <div class="flex items-start justify-between mb-4">
                    <div class="flex items-center space-x-3">
                        <div class="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                            <span class="text-blue-600 font-semibold">{avis.user.username[0].upper()}</span>
                        </div>
                        <div>
                            <div class="font-medium text-gray-900">{avis.user.username}</div>
                            <div class="text-sm text-gray-500">{avis.date_creation.strftime("%d %B %Y")}</div>
                        </div>
                    </div>
                    <div class="text-yellow-400 text-lg">{stars}</div>
                </div>
                <div class="text-gray-700 leading-relaxed">{avis.commentaire}</div>
            </div>
            '''
        
        if not page_obj:
            avis_html = '''
            <div class="text-center py-8">
                <i class="fas fa-comments text-4xl text-gray-300 mb-4"></i>
                <h4 class="text-lg font-medium text-gray-900 mb-2">Aucun avis pour le moment</h4>
                <p class="text-gray-600">Soyez le premier à partager votre expérience !</p>
            </div>
            '''
        
        avis_html += '</div>'
        
        return JsonResponse({
            'avis_html': avis_html,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
        })
        
    except Exception as e:
        print(f"Erreur lors de la récupération des avis: {e}")
        return JsonResponse({
            'avis_html': f'<p>Erreur: {str(e)}</p>',
            'has_next': False,
            'has_previous': False,
            'current_page': 1,
            'total_pages': 1,
        })