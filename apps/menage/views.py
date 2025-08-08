# ==========================================
# apps/menage/views.py - Planning ménage basique
# ==========================================
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone

from apps.users.views import is_gestionnaire
from .models import TacheMenage
from .forms import TacheMenageForm

@login_required
@user_passes_test(is_gestionnaire)
def planning_menage(request):
    """Liste des appartements à nettoyer selon cahier"""
    today = timezone.now().date()
    
    # Tâches par statut
    taches_urgentes = TacheMenage.objects.filter(
        statut='a_faire',
        date_prevue__lte=today
    ).select_related('appartement', 'reservation__client')
    
    taches_a_venir = TacheMenage.objects.filter(
        statut='a_faire',
        date_prevue__gt=today
    ).select_related('appartement', 'reservation__client')
    
    taches_en_cours = TacheMenage.objects.filter(
        statut='en_cours'
    ).select_related('appartement', 'personnel')
    
    context = {
        'taches_urgentes': taches_urgentes,
        'taches_a_venir': taches_a_venir,
        'taches_en_cours': taches_en_cours,
        'today': today,
    }
    return render(request, 'menage/planning.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def checklist_menage(request, pk):
    """Check-list simple selon cahier"""
    tache = get_object_or_404(TacheMenage, pk=pk)
    
    if request.method == 'POST':
        form = TacheMenageForm(request.POST, request.FILES, instance=tache)
        if form.is_valid():
            tache_updated = form.save(commit=False)
            
            # Si tout est fait, marquer comme terminé
            if (tache_updated.menage_general_fait and 
                tache_updated.equipements_verifies and 
                not tache_updated.problemes_signales):
                tache_updated.statut = 'termine'
                tache_updated.date_completion = timezone.now()
            
            tache_updated.personnel = request.user
            tache_updated.save()
            
            messages.success(request, f'Check-list {tache.appartement.numero} mise à jour !')
            return redirect('menage:planning')
    else:
        form = TacheMenageForm(instance=tache)
    
    context = {
        'form': form,
        'tache': tache,
    }
    return render(request, 'menage/checklist.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def taches_urgentes(request):
    """Tâches urgentes selon cahier"""
    today = timezone.now().date()
    
    taches_urgentes = TacheMenage.objects.filter(
        statut='a_faire',
        date_prevue__lte=today
    ).select_related('appartement', 'reservation__client').order_by('date_prevue')
    
    context = {
        'taches_urgentes': taches_urgentes,
        'today': today,
    }
    return render(request, 'menage/urgentes.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def terminer_tache(request, pk):
    """Terminer une tâche de ménage selon cahier"""
    tache = get_object_or_404(TacheMenage, pk=pk)
    
    # Vérifier que la check-list est complète selon cahier
    if not tache.menage_general_fait or not tache.equipements_verifies:
        messages.error(request, 'La check-list doit être complète pour terminer')
        return redirect('menage:checklist', pk=pk)
    
    # Marquer comme terminé selon cahier
    tache.statut = 'termine'
    tache.date_completion = timezone.now()
    tache.personnel = request.user
    tache.save()
    
    # Changer le statut de l'appartement en disponible
    tache.appartement.statut = 'disponible'
    tache.appartement.save()
    
    messages.success(request, f'Ménage {tache.appartement.numero} terminé ! Appartement marqué disponible.')
    return redirect('menage:planning')

@login_required
@user_passes_test(is_gestionnaire)
def generer_tache_apres_depart(request, reservation_pk):
    """
    Génération automatique de tâche ménage après départ selon cahier
    """
    from apps.reservations.models import Reservation
    reservation = get_object_or_404(Reservation, pk=reservation_pk)
    
    # Créer tâche ménage selon cahier
    tache, created = TacheMenage.objects.get_or_create(
        appartement=reservation.appartement,
        reservation=reservation,
        defaults={
            'date_prevue': reservation.date_depart,
            'statut': 'a_faire'
        }
    )
    
    if created:
        # Marquer appartement en maintenance
        reservation.appartement.statut = 'maintenance'
        reservation.appartement.save()
        
        messages.success(request, f'Tâche ménage créée pour {reservation.appartement.numero}')
    else:
        messages.info(request, 'Tâche ménage déjà existante')
    
    return redirect('menage:planning')

#historique_menage
@login_required
@user_passes_test(is_gestionnaire)
def historique_menage(request):
    """Historique des tâches ménage selon cahier"""
    from apps.appartements.models import Appartement
    appartements = Appartement.objects.all()
    
    context = {
        'appartements': appartements,
    }
    return render(request, 'menage/historique.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def programmer_menage(request, appartement_pk):
    """Programmer ménage pour un appartement"""
    from apps.appartements.models import Appartement
    appartement = get_object_or_404(Appartement, pk=appartement_pk)
    
    if request.method == 'POST':
        date_prevue = request.POST.get('date_prevue')
        
        if date_prevue:
            tache, created = TacheMenage.objects.get_or_create(
                appartement=appartement,
                date_prevue=date_prevue,
                statut='a_faire',
                defaults={
                    'personnel': request.user
                }
            )
            
            if created:
                messages.success(request, f'Ménage programmé pour {appartement.numero} le {date_prevue}')
            else:
                messages.info(request, 'Ménage déjà programmé pour cette date')
        else:
            messages.error(request, 'Date requise')
            
        return redirect('appartements:detail', pk=appartement_pk)
    
    # GET - Afficher le formulaire simple
    today = timezone.now().date()
    
    context = {
        'appartement': appartement,
        'today': today,
        'taches_existantes': TacheMenage.objects.filter(
            appartement=appartement,
            statut__in=['a_faire', 'en_cours']
        )
    }
    return render(request, 'menage/programmer.html', context)