from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from apps.users.views import is_gestionnaire
from .models import TacheMenage


@login_required
@user_passes_test(is_gestionnaire)
def planning_menage(request):
    """Liste des tâches de ménage"""
    today = timezone.now().date()
    
    # Tâches urgentes (date passée ou aujourd'hui)
    taches_urgentes = TacheMenage.objects.filter(
        statut='a_faire',
        date_prevue__lte=today
    ).select_related('appartement', 'reservation')
    
    # Tâches à venir
    taches_a_venir = TacheMenage.objects.filter(
        statut='a_faire',
        date_prevue__gt=today
    ).select_related('appartement', 'reservation').order_by('date_prevue')[:20]
    
    # Tâches en cours
    taches_en_cours = TacheMenage.objects.filter(
        statut='en_cours'
    ).select_related('appartement')
    
    # Tâches terminées récentes (7 derniers jours)
    taches_terminees = TacheMenage.objects.filter(
        statut='termine',
        date_completion__gte=today - timezone.timedelta(days=7)
    ).select_related('appartement').order_by('-date_completion')
    
    context = {
        'taches_urgentes': taches_urgentes,
        'taches_a_venir': taches_a_venir,
        'taches_en_cours': taches_en_cours,
        'taches_terminees': taches_terminees,
    }
    return render(request, 'menage/planning.html', context)


@login_required
@user_passes_test(is_gestionnaire)
def detail_tache(request, tache_pk):
    """Détail d'une tâche avec édition du rapport"""
    tache = get_object_or_404(TacheMenage, pk=tache_pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'commencer':
            tache.statut = 'en_cours'
            tache.save()
            messages.success(request, f'Tâche démarrée pour {tache.appartement.numero}')
            
        elif action == 'terminer':
            rapport = request.POST.get('rapport', '').strip()
            
            if not rapport:
                messages.error(request, 'Le rapport est obligatoire pour terminer la tâche')
            else:
                tache.rapport = rapport
                tache.statut = 'termine'
                tache.date_completion = timezone.now()
                tache.save()
                messages.success(request, f'Tâche terminée pour {tache.appartement.numero}')
                return redirect('menage:planning')
        
        elif action == 'sauvegarder':
            rapport = request.POST.get('rapport', '').strip()
            tache.rapport = rapport
            tache.save()
            messages.success(request, 'Rapport sauvegardé')
    
    context = {
        'tache': tache,
    }
    return render(request, 'menage/detail.html', context)


@login_required
@user_passes_test(is_gestionnaire)
def historique_menage(request):
    """Historique complet des tâches"""
    from apps.appartements.models import Appartement
    
    appartements = Appartement.objects.prefetch_related(
        'taches_menage'
    ).all()
    
    # Statistiques
    total_terminees = TacheMenage.objects.filter(statut='termine').count()
    total_en_cours = TacheMenage.objects.filter(statut='en_cours').count()
    total_a_faire = TacheMenage.objects.filter(statut='a_faire').count()
    
    context = {
        'appartements': appartements,
        'total_terminees': total_terminees,
        'total_en_cours': total_en_cours,
        'total_a_faire': total_a_faire,
    }
    return render(request, 'menage/historique.html', context)