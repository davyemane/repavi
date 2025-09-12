# ==========================================
# apps/comptabilite/views.py - Comptabilité simple
# ==========================================
import csv
from django.contrib import messages  # ✅ Import correct
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from datetime import datetime

from apps.comptabilite.forms import MouvementComptableForm
from apps.users.views import is_gestionnaire
from .models import ComptabiliteAppartement


@login_required
@user_passes_test(is_gestionnaire)
def rapport_mensuel(request):
    """Vue mensuelle simple selon cahier - PAS de calculs complexes"""
    # Mois sélectionné
    annee = int(request.GET.get('annee', datetime.now().year))
    mois = int(request.GET.get('mois', datetime.now().month))
    
    from apps.appartements.models import Appartement
    appartements = Appartement.objects.all()
    
    rapport_data = []
    total_revenus = 0
    total_charges = 0
    
    for appartement in appartements:
        # Revenus du mois (addition simple selon cahier)
        revenus = ComptabiliteAppartement.get_revenus_mois(appartement, annee, mois)
        
        # Charges du mois (soustraction simple selon cahier)
        charges = ComptabiliteAppartement.get_charges_mois(appartement, annee, mois)
        
        # Résultat simple
        resultat = revenus - charges
        
        # Pourcentage d'occupation simple selon cahier
        from apps.reservations.models import Reservation
        from calendar import monthrange
        
        jours_mois = monthrange(annee, mois)[1]
        nuits_occupees = 0
        
        for res in Reservation.objects.filter(
            appartement=appartement,
            statut__in=['confirmee', 'en_cours', 'terminee'],
            date_arrivee__year=annee,
            date_arrivee__month=mois
        ):
            debut_mois = datetime(annee, mois, 1).date()
            fin_mois = datetime(annee, mois, jours_mois).date()
            
            debut_sejour = max(res.date_arrivee, debut_mois)
            fin_sejour = min(res.date_depart, fin_mois)
            
            if debut_sejour < fin_sejour:
                nuits_occupees += (fin_sejour - debut_sejour).days
        
        taux_occupation = round((nuits_occupees / jours_mois) * 100) if jours_mois > 0 else 0
        
        rapport_data.append({
            'appartement': appartement,
            'revenus': revenus,
            'charges': charges,
            'resultat': resultat,
            'nuits_occupees': nuits_occupees,
            'taux_occupation': taux_occupation,
        })
        
        total_revenus += revenus
        total_charges += charges
    
    context = {
        'rapport_data': rapport_data,
        'annee': annee,
        'mois': mois,
        'mois_nom': datetime(annee, mois, 1).strftime('%B %Y'),
        'total_revenus': total_revenus,
        'total_charges': total_charges,
        'resultat_global': total_revenus - total_charges,
        'annees': [2023, 2024, 2025],  # ✅ AJOUTER
        'mois_liste': list(range(1, 13)),  # ✅ AJOUTER

    }
    return render(request, 'comptabilite/rapport_mensuel.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def ajouter_mouvement(request):
    """
    Ajouter un mouvement comptable selon cahier
    Addition/soustraction simple - PAS de calculs complexes
    """
    if request.method == 'POST':
        form = MouvementComptableForm(request.POST)
        if form.is_valid():
            mouvement = form.save(commit=False)
            mouvement.gestionnaire = request.user
            mouvement.save()
            
            # Créer mouvement dans la comptabilité
            if mouvement.type_mouvement == 'revenu':
                messages.success(request, f'Revenu de {mouvement.montant:,.0f} FCFA ajouté pour {mouvement.appartement.numero}')
            else:
                messages.success(request, f'Charge de {mouvement.montant:,.0f} FCFA ajoutée pour {mouvement.appartement.numero}')
            
            return redirect('comptabilite:rapport_mensuel')
    else:
        form = MouvementComptableForm()
        
        # Pré-sélectionner appartement si fourni
        appartement_id = request.GET.get('appartement')
        if appartement_id:
            form.fields['appartement'].initial = appartement_id
    
    context = {
        'form': form,
        'titre': 'Ajouter un Mouvement Comptable',
    }
    return render(request, 'comptabilite/ajouter_mouvement.html', context)


def clean_int_param(value, default):
    """Nettoie et convertit un paramètre en entier"""
    try:
        if isinstance(value, str):
            # Supprimer espaces, espaces insécables, et autres caractères invisibles
            cleaned = ''.join(c for c in value if c.isdigit())
            return int(cleaned) if cleaned else default
        return int(value)
    except (ValueError, TypeError):
        return default

@login_required
@user_passes_test(is_gestionnaire)
def detail_appartement(request, appartement_pk):
    """
    Détail comptable d'un appartement selon cahier
    Vue simple : revenus - charges = résultat
    """
    from apps.appartements.models import Appartement
    appartement = get_object_or_404(Appartement, pk=appartement_pk)
    
    # Mois sélectionné
    annee = clean_int_param(request.GET.get('annee'), datetime.now().year)
    mois = clean_int_param(request.GET.get('mois'), datetime.now().month)    
    # Mouvements du mois
    mouvements = ComptabiliteAppartement.objects.filter(
        appartement=appartement,
        date_mouvement__year=annee,
        date_mouvement__month=mois
    ).order_by('-date_mouvement')
    
    # Calculs simples selon cahier
    revenus = ComptabiliteAppartement.get_revenus_mois(appartement, annee, mois)
    charges = ComptabiliteAppartement.get_charges_mois(appartement, annee, mois)
    resultat = revenus - charges
    
    # Réservations du mois pour occupation
    from apps.reservations.models import Reservation
    reservations_mois = Reservation.objects.filter(
        appartement=appartement,
        date_arrivee__year=annee,
        date_arrivee__month=mois
    )
    
    context = {
        'appartement': appartement,
        'annee': annee,
        'mois': mois,
        'mois_nom': datetime(annee, mois, 1).strftime('%B %Y'),
        'mouvements': mouvements,
        'revenus': revenus,
        'charges': charges,
        'resultat': resultat,
        'reservations_mois': reservations_mois,
        'annees': [2023, 2024, 2025],  # ✅ AJOUTER
        'mois_liste': list(range(1, 13)),  # ✅ AJOUTER
    }
    return render(request, 'comptabilite/detail_appartement.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def export_rapport(request, annee, mois):
    """Export CSV du rapport mensuel selon cahier"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="rapport_repavi_{annee}_{mois:02d}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Appartement', 'Type', 'Revenus (FCFA)', 'Charges (FCFA)', 
        'Résultat (FCFA)', 'Taux Occupation (%)'
    ])
    
    from apps.appartements.models import Appartement
    for appartement in Appartement.objects.all():
        revenus = ComptabiliteAppartement.get_revenus_mois(appartement, annee, mois)
        charges = ComptabiliteAppartement.get_charges_mois(appartement, annee, mois)
        resultat = revenus - charges
        
        # Calcul taux occupation simple
        # TODO: Implémenter calcul selon cahier
        taux_occupation = 0
        
        writer.writerow([
            appartement.numero,
            appartement.get_type_logement_display(),
            revenus,
            charges,
            resultat,
            taux_occupation
        ])
    
    return response

# modifier_mouvement
@login_required
@user_passes_test(is_gestionnaire)
def modifier_mouvement(request, pk):
    """Modifier un mouvement selon cahier"""
    mouvement = get_object_or_404(ComptabiliteAppartement, pk=pk)
    
    if request.method == 'POST':
        form = MouvementComptableForm(request.POST, instance=mouvement)
        if form.is_valid():
            mouvement = form.save(commit=False)
            mouvement.gestionnaire = request.user
            mouvement.save()
            
            messages.success(request, f'Mouvement {mouvement.type_mouvement} modifié avec succès !')
            return redirect('comptabilite:rapport_mensuel')
    else:
        form = MouvementComptableForm(instance=mouvement)
    
    context = {
        'form': form,
        'mouvement': mouvement,
        'titre': f'Modifier {mouvement.type_mouvement}',
    }
    return render(request, 'comptabilite/modifier_mouvement.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def supprimer_mouvement(request, pk):
    """Supprimer un mouvement selon cahier"""
    mouvement = get_object_or_404(ComptabiliteAppartement, pk=pk)
    
    if request.method == 'POST':
        mouvement.delete()
        messages.success(request, f'Mouvement {mouvement.type_mouvement} supprimé avec succès !')
        return redirect('comptabilite:rapport_mensuel')
    
    context = {
        'mouvement': mouvement,
        'titre': f'Supprimer {mouvement.type_mouvement}',
    }
    return render(request, 'comptabilite/supprimer_mouvement.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def detail_mouvement(request, pk):
    """Détail d'un mouvement selon cahier"""
    mouvement = get_object_or_404(ComptabiliteAppartement, pk=pk)
    
    context = {
        'mouvement': mouvement,
    }        
    return render(request, 'comptabilite/detail_mouvement.html', context)



