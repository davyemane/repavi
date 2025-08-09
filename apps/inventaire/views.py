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
def inventaire_general(request):
    """Inventaire général selon cahier"""
    appartements = Appartement.objects.all()
    
    # Statistiques globales
    total_equipements = EquipementAppartement.objects.count()
    equipements_defectueux = EquipementAppartement.objects.filter(etat='defectueux').count()
    equipements_hors_service = EquipementAppartement.objects.filter(etat='hors_service').count()
    valeur_totale = EquipementAppartement.objects.aggregate(total=Sum('prix_achat'))['total'] or 0
    
    # Données par appartement
    appartements_data = []
    for appartement in appartements:
        equipements = appartement.inventaire_equipements.all()  # Utilisation du nouveau related_name
        stats_etats = {}
        for etat_code, etat_nom in EquipementAppartement.ETAT_CHOICES:
            stats_etats[etat_code] = {
                'nom': etat_nom,
                'count': equipements.filter(etat=etat_code).count()
            }
        
        appartements_data.append({
            'appartement': appartement,
            'equipements': equipements,
            'nb_equipements': equipements.count(),
            'valeur_totale': equipements.aggregate(total=Sum('prix_achat'))['total'] or 0,
            'stats_etats': stats_etats,
        })
    
    context = {
        'appartements_data': appartements_data,
        'total_equipements': total_equipements,
        'equipements_defectueux': equipements_defectueux,
        'equipements_hors_service': equipements_hors_service,
        'valeur_totale': valeur_totale,
    }
    return render(request, 'inventaire/general.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def inventaire_par_appartement(request, appartement_pk):
    """Inventaire par appartement selon cahier"""
    appartement = get_object_or_404(Appartement, pk=appartement_pk)
    
    equipements = appartement.inventaire_equipements.all()  # Utilisation du nouveau related_name
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
def ajouter_equipement(request, appartement_pk):
    """Ajouter un équipement selon cahier"""
    appartement = get_object_or_404(Appartement, pk=appartement_pk)
    
    if request.method == 'POST':
        form = EquipementForm(request.POST, request.FILES)
        if form.is_valid():
            equipement = form.save(commit=False)
            equipement.appartement = appartement
            equipement.save()
            
            messages.success(request, f'Équipement {equipement.nom} ajouté avec succès !')
            return redirect('inventaire:appartement', appartement_pk=appartement.pk)
    else:
        form = EquipementForm()
    
    # Équipements suggérés selon cahier
    equipements_sugges = [
        'TV', 'Frigo', 'Climatisation', 'Micro-ondes', 'Bouilloire', 
        'Canapé', 'Table basse', 'Lit double', 'Armoire', 'Chaises',
        'Wifi', 'Balcon', 'Parking', 'Sécurité 24h', 'Générateur'
    ]
    
    context = {
        'form': form,
        'appartement': appartement,
        'titre': f'Ajouter un équipement - {appartement.numero}',
        'equipements_sugges': equipements_sugges,
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
            equipement = form.save()
            
            messages.success(request, f'Équipement {equipement.nom} modifié avec succès !')
            return redirect('inventaire:appartement', appartement_pk=equipement.appartement.pk)
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
        appartement_pk = equipement.appartement.pk
        equipement.delete()
        messages.success(request, f'Équipement {equipement.nom} supprimé avec succès !')
        return redirect('inventaire:appartement', appartement_pk=appartement_pk)
    
    context = {
        'equipement': equipement,
        'titre': f'Supprimer {equipement.nom}',
    }
    return render(request, 'inventaire/supprimer_equipement.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def valeur_totale_appartement(request, appartement_pk):
    """Valeur totale d'un appartement selon cahier"""
    appartement = get_object_or_404(Appartement, pk=appartement_pk)
    
    equipements = appartement.inventaire_equipements.all()  # Utilisation du nouveau related_name
    valeur_totale = equipements.aggregate(total=Sum('prix_achat'))['total'] or 0
    
    # Détail par état
    valeurs_par_etat = {}
    for etat_code, etat_nom in EquipementAppartement.ETAT_CHOICES:
        equipements_etat = equipements.filter(etat=etat_code)
        valeurs_par_etat[etat_code] = {
            'nom': etat_nom,
            'count': equipements_etat.count(),
            'valeur': equipements_etat.aggregate(total=Sum('prix_achat'))['total'] or 0
        }
    
    # Calculs pour indicateurs de santé
    total_count = equipements.count()
    bon_count = valeurs_par_etat['bon']['count']
    pourcentage_bon = (bon_count / total_count * 100) if total_count > 0 else 0
    
    # Classe CSS selon pourcentage
    if pourcentage_bon >= 80:
        classe_sante = 'text-green-600'
        bg_sante = 'bg-green-500'
    elif pourcentage_bon >= 60:
        classe_sante = 'text-orange-600'
        bg_sante = 'bg-orange-500'
    else:
        classe_sante = 'text-red-600'
        bg_sante = 'bg-red-500'
    
    context = {
        'appartement': appartement,
        'equipements': equipements,
        'valeur_totale': valeur_totale,
        'valeurs_par_etat': valeurs_par_etat,
        'pourcentage_bon': pourcentage_bon,
        'classe_sante': classe_sante,
        'bg_sante': bg_sante,
    }
    return render(request, 'inventaire/valeur_totale_appartement.html', context)