# ==========================================
# apps/paiements/views.py - Paiements par tranches SIMPLIFIÉ
# ==========================================
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone

from apps.reservations.models import Reservation
from apps.users.views import is_gestionnaire
from .models import EcheancierPaiement
from .forms import PaiementForm

@login_required
@user_passes_test(is_gestionnaire)
def echeancier_paiements(request):
    """Tableau des échéances selon cahier"""
    # Filtres
    statut_filtre = request.GET.get('statut', 'tous')
    
    paiements = EcheancierPaiement.objects.select_related(
        'reservation__client', 
        'reservation__appartement'
    ).order_by('date_echeance')
    
    if statut_filtre == 'en_attente':
        paiements = paiements.filter(statut='en_attente')
    elif statut_filtre == 'retard':
        paiements = paiements.filter(
            statut='en_attente',
            date_echeance__lt=timezone.now().date()
        )
    
    context = {
        'paiements': paiements,
        'statut_filtre': statut_filtre,
    }
    return render(request, 'paiements/echeancier.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def saisir_paiement(request, pk):
    """Enregistrer un paiement reçu selon cahier"""
    echeance = get_object_or_404(EcheancierPaiement, pk=pk)
    
    if request.method == 'POST':
        form = PaiementForm(request.POST, instance=echeance)
        if form.is_valid():
            paiement = form.save(commit=False)
            paiement.date_paiement = timezone.now().date()
            paiement.statut = 'paye'
            paiement.save()
            
            messages.success(request, 'Paiement enregistré avec succès !')
            return redirect('paiements:echeancier')
    else:
        form = PaiementForm(instance=echeance)
    
    context = {
        'form': form,
        'echeance': echeance,
        'reservation': echeance.reservation,
    }
    return render(request, 'paiements/saisir.html', context)

#paiements_en_retard
@login_required
@user_passes_test(is_gestionnaire)
def paiements_en_retard(request):
    """Historique des paiements en retard selon cahier"""
    from apps.reservations.models import Reservation
    reservations = Reservation.objects.filter(statut='en_attente').order_by('-date_echeance')
    
    context = {
        'reservations': reservations,
    }
    return render(request, 'paiements/paiements_en_retard.html', context)


# modifier_paiement et generer_echeancier
@login_required
@user_passes_test(is_gestionnaire)
def modifier_paiement(request, pk):
    """Modifier un paiement selon cahier"""
    echeance = get_object_or_404(EcheancierPaiement, pk=pk)
    
    if request.method == 'POST':
        form = PaiementForm(request.POST, instance=echeance)
        if form.is_valid():
            paiement = form.save(commit=False)
            paiement.gestionnaire = request.user
            paiement.save()
            
            messages.success(request, f'Paiement {paiement.get_type_paiement_display()} modifié avec succès !')
            return redirect('paiements:echeancier')
    else:
        form = PaiementForm(instance=echeance)
    
    context = {
        'form': form,
        'echeance': echeance,
        'reservation': echeance.reservation,
    }
    return render(request, 'paiements/modifier_paiement.html', context)

@login_required
@user_passes_test(is_gestionnaire)      
def generer_echeancier(request):
    """Générer un échéancier selon cahier"""
    if request.method == 'POST':
        reservation_id = request.POST.get('reservation_id')
        if not reservation_id:
            messages.error(request, 'Veuillez sélectionner une réservation')
            return redirect('paiements:echeancier')
        
        reservation = get_object_or_404(Reservation, pk=reservation_id)
        
        # Créer l'échéancier selon cahier
        echeance = EcheancierPaiement.objects.create(
            reservation=reservation,
            type_paiement='echeance',
            montant_prevu=reservation.prix_total,
            date_echeance=reservation.date_arrivee - timedelta(days=7)
        )
        
        # Générer le PDF selon cahier
        pdf_file = generer_pdf_echeancier(echeance)
        echeance.fichier_pdf.save(
            f'echeancier_{echeance.id}.pdf',
            pdf_file,
            save=True
        )
        
        messages.success(request, f'Échéancier généré avec succès !')
        return redirect('paiements:echeancier')
    else:
        messages.error(request, 'Veuillez utiliser le formulaire de recherche.')
        return redirect('paiements:echeancier')

# generer_pdf_echeancier
def generer_pdf_echeancier(echeance):
    """Générer le PDF de l'échéancier selon cahier"""
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Ajouter le contenu du PDF selon cahier
    p.drawString(100, 750, f'Échéancier pour la réservation {echeance.reservation.id}')
    p.drawString(100, 730, f'Montant prévu: {echeance.montant_prevu} €')
    p.drawString(100, 710, f'Date d\'échéance: {echeance.date_echeance}')
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer   