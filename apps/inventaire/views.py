# ==========================================
# apps/inventaire/views.py - Inventaire équipements SIMPLIFIÉ  
# ==========================================
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum

from apps.appartements.models import Appartement
from apps.users.views import is_gestionnaire
from .models import EquipementAppartement
from .forms import EquipementForm

@login_required
@user_passes_test(is_gestionnaire)
def inventaire_par_appartement(request, appartement_pk):
    """Inventaire par appartement selon cahier"""
    from apps.appartements.models import Appartement
    appartement = get_object_or_404(Appartement, pk=appartement_pk)
    
    equipements = EquipementAppartement.objects.filter(appartement=appartement)
    valeur_totale = equipements.aggregate(total=Sum('prix_achat'))['total'] or 0
    
    # Statistiques par état
    stats_etats = {}
    for etat_code, etat_nom in EquipementAppartement.ETAT_CHOICES:
        stats_etats[etat_code] = {
            'nom': etat_nom,
            'count': equipements.filter(etat=etat_code).count()
        }
    
    context = {
        'appartement': appartement,
        'equipements': equipements,
        'valeur_totale': valeur_totale,
        'stats_etats': stats_etats,
    }
    return render(request, 'inventaire/par_appartement.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def changer_etat_equipement(request, pk):
    """Changer état d'un équipement en 1 clic selon cahier"""
    equipement = get_object_or_404(EquipementAppartement, pk=pk)
    nouvel_etat = request.GET.get('etat')
    commentaire = request.GET.get('commentaire', '')
    
    if nouvel_etat in dict(EquipementAppartement.ETAT_CHOICES):
        equipement.etat = nouvel_etat
        if commentaire:
            equipement.commentaire = commentaire
        equipement.save()
        
        messages.success(request, f'État de {equipement.nom} changé en {equipement.get_etat_display()}')
    
    return redirect('inventaire:appartement', appartement_pk=equipement.appartement.pk)

@login_required
@user_passes_test(is_gestionnaire)
def inventaire_general(request):
    """Inventaire général selon cahier"""
    from apps.appartements.models import Appartement
    appartements = Appartement.objects.all().prefetch_related('equipements')
    
    # Valeur totale par appartement
    valeur_totale = sum(eq.prix_achat for eq in appartements.all())
    
    context = {
        'appartements': appartements,
        'valeur_totale': valeur_totale,
    }
    return render(request, 'inventaire/general.html', context)

#ajouter équipement
@login_required
@user_passes_test(is_gestionnaire)
def ajouter_equipement(request):
    """Ajouter un équipement selon cahier"""
    if request.method == 'POST':
        form = EquipementForm(request.POST, request.FILES)
        if form.is_valid():
            equipement = form.save(commit=False)
            equipement.gestionnaire = request.user
            equipement.save()
            
            messages.success(request, f'Équipement {equipement.nom} ajouté avec succès !')
            return redirect('inventaire:general')
    else:
        form = EquipementForm()
    
    context = {
        'form': form,
        'titre': 'Ajouter un équipement',
    }
    return render(request, 'inventaire/ajouter_equipement.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def modifier_equipement(request, pk):
    """Modifier un équipement selon cahier"""
    equipement = get_object_or_404(EquipementAppartement, pk=pk)
    
    if request.method == 'POST':
        form = EquipementForm(request.POST, request.FILES, instance=equipement)
        if form.is_valid():
            equipement = form.save(commit=False)
            equipement.gestionnaire = request.user
            equipement.save()
            
            messages.success(request, f'Équipement {equipement.nom} modifié avec succès !')
            return redirect('inventaire:general')
    else:
        form = EquipementForm(instance=equipement)
    
    context = {
        'form': form,
        'equipement': equipement,
        'titre': f'Modifier {equipement.nom}',
    }
    return render(request, 'inventaire/modifier_equipement.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def supprimer_equipement(request, pk):
    """Supprimer un équipement selon cahier"""
    equipement = get_object_or_404(EquipementAppartement, pk=pk)
    
    if request.method == 'POST':
        equipement.delete()
        messages.success(request, f'Équipement {equipement.nom} supprimé avec succès !')
        return redirect('inventaire:general')
    
    context = {
        'equipement': equipement,
        'titre': f'Supprimer {equipement.nom}',
    }
    return render(request, 'inventaire/supprimer_equipement.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def changer_etat_equipement(request, pk):
    """Changer état d'un équipement selon cahier"""
    equipement = get_object_or_404(EquipementAppartement, pk=pk)
    nouvel_etat = request.GET.get('etat')
    commentaire = request.GET.get('commentaire', '')
    
    if nouvel_etat in dict(EquipementAppartement.ETAT_CHOICES):
        equipement.etat = nouvel_etat
        if commentaire:
            equipement.commentaire = commentaire
        equipement.save()
        
        messages.success(request, f'État de {equipement.nom} changé en {equipement.get_etat_display()}')
    
    return redirect('inventaire:general')

@login_required
@user_passes_test(is_gestionnaire)
def valeur_totale_appartement(request, appartement_pk):
    """Valeur totale d'un appartement selon cahier"""
    appartement = get_object_or_404(Appartement, pk=appartement_pk)
    
    # Valeur totale par équipement
    valeur_totale = sum(eq.prix_achat for eq in appartement.equipements.all())
    
    context = {
        'appartement': appartement,
        'valeur_totale': valeur_totale,
    }
    return render(request, 'inventaire/valeur_totale_appartement.html', context)