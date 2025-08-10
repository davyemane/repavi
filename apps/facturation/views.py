# ==========================================
# apps/facturation/views.py - Facturation avec service
# ==========================================
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import FileResponse, Http404
from django.urls import reverse

from apps.notifications.services import NotificationService
from apps.users.views import is_gestionnaire
from apps.reservations.models import Reservation
from .models import Facture
from .forms import FactureForm
from .services import FacturationService

@login_required
@user_passes_test(is_gestionnaire)
def liste_factures(request):
    """Liste des factures générées"""
    factures = Facture.objects.select_related(
        'reservation__client',
        'reservation__appartement'
    ).order_by('-date_creation')
    
    # Stats
    stats = {
        'total_factures': factures.count(),
        'montant_total': sum(f.montant_total for f in factures),
        'factures_mois': factures.filter(date_creation__month=timezone.now().month).count()
    }
    
    context = {
        'factures': factures,
        **stats
    }
    return render(request, 'facturation/liste.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def generer_facture(request):
    """Générer nouvelle facture"""
    reservations_facturables = FacturationService.get_reservations_facturables()
    
    if request.method == 'POST':
        reservation_id = request.POST.get('reservation_id')
        frais_supplementaires = request.POST.get('frais_supplementaires', 0)
        
        if not reservation_id:
            messages.error(request, 'Veuillez sélectionner une réservation')
            return redirect('facturation:generer')
        
        try:
            reservation = get_object_or_404(Reservation, pk=reservation_id)
            
            # Vérifier si facture existe déjà
            if hasattr(reservation, 'facture'):
                messages.warning(request, 'Une facture existe déjà pour cette réservation')
                return redirect('facturation:apercu', pk=reservation.facture.pk)
            
            # Créer facture via service
            facture = FacturationService.creer_facture(
                reservation=reservation,
                frais_supplementaires=frais_supplementaires,
                gestionnaire=request.user
            )
            # notification pour les gestionnaires
            NotificationService.notify_facture_created(facture, request.user)
            
            messages.success(request, f'Facture {facture.numero_facture} générée avec succès !')
            return redirect('facturation:apercu', pk=facture.pk)
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la génération : {str(e)}')
    
    context = {
        'reservations_facturables': reservations_facturables,
        'form': FactureForm()
    }
    return render(request, 'facturation/generer.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def generer_facture_reservation(request, reservation_pk):
    """Générer facture depuis réservation"""
    reservation = get_object_or_404(Reservation, pk=reservation_pk)
    
    # Vérifier si facture existe
    if hasattr(reservation, 'facture'):
        messages.info(request, 'Facture déjà existante')
        return redirect('facturation:apercu', pk=reservation.facture.pk)
    
    # Vérifier statut
    if reservation.statut != 'terminee':
        messages.error(request, 'La réservation doit être terminée pour facturer')
        return redirect('reservations:detail', pk=reservation.pk)
    
    try:
        facture = FacturationService.creer_facture(
            reservation=reservation,
            gestionnaire=request.user
        )
        
        messages.success(request, f'Facture {facture.numero_facture} générée !')
        return redirect('facturation:apercu', pk=facture.pk)
        
    except Exception as e:
        messages.error(request, f'Erreur : {str(e)}')
        return redirect('reservations:detail', pk=reservation.pk)

@login_required
@user_passes_test(is_gestionnaire)
def apercu_facture(request, pk):
    """Aperçu facture"""
    facture = get_object_or_404(Facture, pk=pk)
    
    # Calculs pour l'aperçu
    context = {
        'facture': facture,
        'reservation': facture.reservation,
        'client': facture.reservation.client,
        'appartement': facture.reservation.appartement,
        'peut_regenerer': True,
    }
    return render(request, 'facturation/apercu.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def telecharger_pdf(request, pk):
    """Télécharger PDF facture"""
    facture = get_object_or_404(Facture, pk=pk)
    
    # Régénérer si fichier manquant
    if not facture.fichier_pdf or not facture.fichier_pdf.storage.exists(facture.fichier_pdf.name):
        try:
            FacturationService.regenerer_pdf(facture)
            messages.info(request, 'PDF régénéré automatiquement')
        except Exception as e:
            messages.error(request, f'Erreur génération PDF : {str(e)}')
            return redirect('facturation:apercu', pk=pk)
    
    try:
        return FileResponse(
            facture.fichier_pdf.open('rb'),
            as_attachment=True,
            filename=f'Facture_{facture.numero_facture}.pdf'
        )
    except FileNotFoundError:
        raise Http404("Fichier PDF non trouvé")

@login_required
@user_passes_test(is_gestionnaire)
def regenerer_pdf(request, pk):
    """Régénérer PDF"""
    facture = get_object_or_404(Facture, pk=pk)
    
    try:
        FacturationService.regenerer_pdf(facture)
        messages.success(request, 'PDF régénéré avec succès !')
    except Exception as e:
        messages.error(request, f'Erreur régénération : {str(e)}')
    
    return redirect('facturation:apercu', pk=pk)

@login_required
@user_passes_test(is_gestionnaire)
def supprimer_facture(request, pk):
    """Supprimer facture"""
    facture = get_object_or_404(Facture, pk=pk)
    
    if request.method == 'POST':
        numero = facture.numero_facture
        
        # Supprimer fichier PDF
        if facture.fichier_pdf:
            facture.fichier_pdf.delete()
        
        facture.delete()
        
        messages.success(request, f'Facture {numero} supprimée')
        return redirect('facturation:liste')
    
    context = {'facture': facture}
    return render(request, 'facturation/confirmer_suppression.html', context)

# API/AJAX endpoints
@login_required
@user_passes_test(is_gestionnaire)
def api_factures_stats(request):
    """API: Stats facturation"""
    from django.http import JsonResponse
    from django.utils import timezone
    
    factures = Facture.objects.all()
    
    stats = {
        'total_factures': factures.count(),
        'montant_total': float(sum(f.montant_total for f in factures)),
        'factures_mois': factures.filter(
            date_creation__month=timezone.now().month
        ).count(),
        'reservations_facturables': FacturationService.get_reservations_facturables().count()
    }
    
    return JsonResponse(stats)