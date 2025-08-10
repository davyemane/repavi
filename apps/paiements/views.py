# ==========================================
# apps/paiements/views.py - Paiements par tranches CORRIGÉ
# ==========================================
from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q

from apps.reservations.models import Reservation
from apps.users.views import is_gestionnaire
from .models import EcheancierPaiement
from .forms import PaiementForm
from apps.notifications.services import NotificationService

@login_required
@user_passes_test(is_gestionnaire)
def echeancier_paiements(request):
    """Tableau des échéances selon cahier - CORRIGÉ"""
    # Filtres
    statut_filtre = request.GET.get('statut', 'tous')
    
    paiements = EcheancierPaiement.objects.select_related(
        'reservation__client', 
        'reservation__appartement'
    ).order_by('date_echeance')
    
    # Statistiques pour l'affichage
    today = timezone.now().date()
    
    if statut_filtre == 'en_attente':
        paiements = paiements.filter(statut='en_attente')
    elif statut_filtre == 'retard':
        paiements = paiements.filter(
            statut='en_attente',
            date_echeance__lt=today
        )
        # Notification pour les gestionnaires
        NotificationService.notify_paiement_overdue(paiements.first())
    elif statut_filtre == 'paye':
        paiements = paiements.filter(statut='paye')
    
    # Stats pour le dashboard
    stats = {
        'paiements_en_attente': EcheancierPaiement.objects.filter(statut='en_attente').count(),
        'paiements_retard': EcheancierPaiement.objects.filter(
            statut='en_attente', 
            date_echeance__lt=today
        ).count(),
        'paiements_payes': EcheancierPaiement.objects.filter(statut='paye').count(),
    }
    
    context = {
        'paiements': paiements,
        'statut_filtre': statut_filtre,
        'today': today,
        **stats
    }
    return render(request, 'paiements/echeancier.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def saisir_paiement(request, pk):
    """Enregistrer un paiement reçu selon cahier - CORRIGÉ"""
    echeance = get_object_or_404(EcheancierPaiement, pk=pk)
    
    # Calculer la situation financière de la réservation
    situation = EcheancierPaiement.get_situation_reservation(echeance.reservation)
    
    if request.method == 'POST':
        form = PaiementForm(request.POST, instance=echeance)
        if form.is_valid():
            paiement = form.save(commit=False)
            paiement.date_paiement = timezone.now().date()
            
            # Vérification du montant
            montant_saisi = paiement.montant_paye
            
            if montant_saisi > 0:
                paiement.statut = 'paye'
                paiement.save()  # Le recalcul se fait automatiquement dans save()
                NotificationService.notify_paiement_received(paiement, request.user)

                
                # Messages informatifs
                if montant_saisi > paiement.montant_prevu:
                    surplus = montant_saisi - paiement.montant_prevu
                    messages.warning(
                        request, 
                        f'Sur-paiement de {surplus} FCFA détecté. L\'échéancier a été recalculé automatiquement.'
                    )
                elif montant_saisi < paiement.montant_prevu:
                    manquant = paiement.montant_prevu - montant_saisi
                    messages.info(
                        request, 
                        f'Paiement partiel enregistré. Il reste {manquant} FCFA à payer sur cette échéance.'
                    )
                
                messages.success(request, 'Paiement enregistré avec succès !')
                return redirect('paiements:echeancier')
            else:
                messages.error(request, 'Le montant doit être supérieur à 0.')
        else:
            messages.error(request, 'Erreur dans le formulaire.')
    else:
        form = PaiementForm(instance=echeance)
    
    context = {
        'form': form,
        'echeance': echeance,
        'reservation': echeance.reservation,
        'situation': situation,
        'today': timezone.now().date(),
    }
    return render(request, 'paiements/saisir.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def paiements_en_retard(request):
    """Historique des paiements en retard selon cahier - CORRIGÉ"""
    today = timezone.now().date()
    
    # Échéances en retard
    echeances_retard = EcheancierPaiement.objects.filter(
        statut='en_attente',
        date_echeance__lt=today
    ).select_related('reservation__client', 'reservation__appartement').order_by('date_echeance')
    
    # Regrouper par réservation
    reservations_retard = []
    for echeance in echeances_retard:
        # Calculer les jours de retard
        jours_retard = (today - echeance.date_echeance).days
        
        # Situation financière
        situation = EcheancierPaiement.get_situation_reservation(echeance.reservation)
        
        reservation_data = {
            'reservation': echeance.reservation,
            'echeance': echeance,
            'jours_retard': jours_retard,
            'situation': situation,
        }
        reservations_retard.append(reservation_data)
    
    # Stats
    total_montant_retard = sum([r['situation']['solde_restant'] for r in reservations_retard])
    retard_moyen = sum([r['jours_retard'] for r in reservations_retard]) / len(reservations_retard) if reservations_retard else 0
    
    # Notification pour les gestionnaires
    NotificationService.notify_paiement_overdue(reservations_retard[0]['echeance'])
    context = {
        'reservations': reservations_retard,
        'total_montant_retard': total_montant_retard,
        'retard_moyen': round(retard_moyen, 1),
    }
    return render(request, 'paiements/paiements_en_retard.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def modifier_paiement(request, pk):
    """Modifier un paiement selon cahier - CORRIGÉ"""
    echeance = get_object_or_404(EcheancierPaiement, pk=pk)
    
    if request.method == 'POST':
        form = PaiementForm(request.POST, instance=echeance)
        if form.is_valid():
            paiement = form.save(commit=False)
            
            # Recalculer le statut
            if paiement.montant_paye > 0:
                paiement.statut = 'paye'
                if not paiement.date_paiement:
                    paiement.date_paiement = timezone.now().date()
            else:
                paiement.statut = 'en_attente'
                paiement.date_paiement = None
            
            paiement.save()  # Recalcul automatique
            
            messages.success(request, f'Paiement {paiement.get_type_paiement_display()} modifié avec succès !')
            return redirect('paiements:echeancier')
    else:
        form = PaiementForm(instance=echeance)
    
    # Situation financière
    situation = EcheancierPaiement.get_situation_reservation(echeance.reservation)
    
    context = {
        'form': form,
        'echeance': echeance,
        'reservation': echeance.reservation,
        'situation': situation,
    }
    return render(request, 'paiements/modifier_paiement.html', context)

@login_required
@user_passes_test(is_gestionnaire)      
def generer_echeancier(request, reservation_pk):
    """Générer/regénérer un échéancier selon cahier - CORRIGÉ"""
    reservation = get_object_or_404(Reservation, pk=reservation_pk)
    
    if request.method == 'POST':
        try:
            # Utiliser le service de réservation pour créer l'échéancier
            from apps.reservations.services import ReservationService
            ReservationService.creer_echeancier(reservation)
            
            messages.success(request, f'Échéancier généré avec succès pour la réservation #{reservation.pk} !')
        except Exception as e:
            messages.error(request, f'Erreur lors de la génération : {str(e)}')
        
        return redirect('paiements:echeancier')
    else:
        messages.error(request, 'Méthode non autorisée.')
        return redirect('paiements:echeancier')