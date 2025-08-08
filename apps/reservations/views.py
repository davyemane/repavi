from django.shortcuts import render

# Create your views here.
# ==========================================
# apps/reservations/views.py - Réservations et planning
# ==========================================
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta

from apps.users.views import is_gestionnaire
from .models import Reservation
from .forms import ReservationForm

@login_required
@user_passes_test(is_gestionnaire)
def calendrier_reservations(request):
    """Vue mensuelle avec couleurs par statut selon cahier"""
    # Mois en cours par défaut
    annee = int(request.GET.get('annee', datetime.now().year))
    mois = int(request.GET.get('mois', datetime.now().month))
    
    # Premier et dernier jour du mois
    premier_jour = datetime(annee, mois, 1).date()
    if mois == 12:
        dernier_jour = datetime(annee + 1, 1, 1).date() - timedelta(days=1)
    else:
        dernier_jour = datetime(annee, mois + 1, 1).date() - timedelta(days=1)
    
    # Réservations du mois
    reservations = Reservation.objects.filter(
        date_arrivee__lte=dernier_jour,
        date_depart__gt=premier_jour
    ).select_related('client', 'appartement')
    
    # Préparer les données pour le calendrier
    from apps.appartements.models import Appartement
    appartements = Appartement.objects.all().order_by('numero')
    
    calendrier_data = []
    for appartement in appartements:
        app_reservations = reservations.filter(appartement=appartement)
        calendrier_data.append({
            'appartement': appartement,
            'reservations': app_reservations
        })
    
    context = {
        'calendrier_data': calendrier_data,
        'annee': annee,
        'mois': mois,
        'mois_nom': datetime(annee, mois, 1).strftime('%B %Y'),
        'premier_jour': premier_jour,
        'dernier_jour': dernier_jour,
    }
    return render(request, 'reservations/calendrier.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def creer_reservation(request):
    """Création de réservation en 5 étapes selon cahier"""
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            try:
                reservation = form.save(commit=False)
                reservation.gestionnaire = request.user
                
                # Vérification des conflits selon cahier
                reservation.full_clean()
                reservation.save()
                
                # Créer l'échéancier de paiement automatiquement
                from apps.paiements.models import EcheancierPaiement
                
                # Acompte (40% par défaut)
                acompte = reservation.prix_total * 0.4
                EcheancierPaiement.objects.create(
                    reservation=reservation,
                    type_paiement='acompte',
                    montant_prevu=acompte,
                    date_echeance=reservation.date_arrivee - timedelta(days=7)
                )
                
                # Solde (60%)
                solde = reservation.prix_total - acompte
                EcheancierPaiement.objects.create(
                    reservation=reservation,
                    type_paiement='solde',
                    montant_prevu=solde,
                    date_echeance=reservation.date_arrivee
                )
                
                messages.success(request, f'Réservation créée avec succès ! Échéancier généré automatiquement.')
                return redirect('reservations:detail', pk=reservation.pk)
                
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
    else:
        form = ReservationForm()
    
    return render(request, 'reservations/formulaire.html', {
        'form': form,
        'titre': 'Nouvelle Réservation',
        'action': 'Créer'
    })

@login_required
@user_passes_test(is_gestionnaire)
def verifier_disponibilite(request):
    """AJAX - Vérifier disponibilité et calculer prix selon cahier"""
    appartement_id = request.GET.get('appartement')
    date_arrivee = request.GET.get('date_arrivee')
    date_depart = request.GET.get('date_depart')
    
    if not all([appartement_id, date_arrivee, date_depart]):
        return JsonResponse({'error': 'Paramètres manquants'})
    
    try:
        from apps.appartements.models import Appartement
        appartement = Appartement.objects.get(pk=appartement_id)
        
        date_arrivee = datetime.strptime(date_arrivee, '%Y-%m-%d').date()
        date_depart = datetime.strptime(date_depart, '%Y-%m-%d').date()
        
        if date_depart <= date_arrivee:
            return JsonResponse({'error': 'Date de départ invalide'})
        
        # Vérifier conflits selon cahier
        conflits = Reservation.objects.filter(
            appartement=appartement,
            statut__in=['confirmee', 'en_cours'],
            date_arrivee__lt=date_depart,
            date_depart__gt=date_arrivee
        )
        
        if conflits.exists():
            return JsonResponse({
                'disponible': False,
                'message': 'Dates non disponibles - conflit détecté'
            })
        
        # Calcul automatique selon cahier
        nombre_nuits = (date_depart - date_arrivee).days
        prix_total = nombre_nuits * appartement.prix_par_nuit
        
        return JsonResponse({
            'disponible': True,
            'nombre_nuits': nombre_nuits,
            'prix_par_nuit': float(appartement.prix_par_nuit),
            'prix_total': float(prix_total),
            'message': f'Disponible - {nombre_nuits} nuits × {appartement.prix_par_nuit} FCFA'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)})
    
    #liste_reservations
@login_required
@user_passes_test(is_gestionnaire)
def liste_reservations(request):
    """Liste des réservations selon cahier"""
    from apps.appartements.models import Appartement
    appartements = Appartement.objects.all()
    
    context = {
        'appartements': appartements,
    }
    return render(request, 'reservations/liste_reservations.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def detail_reservation(request, pk):
    """Détail d'une réservation selon cahier"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    context = {
        'reservation': reservation,
    }        
    return render(request, 'reservations/detail_reservation.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def modifier_reservation(request, pk):
    """Modifier une réservation selon cahier"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    if request.method == 'POST':
        form = ReservationForm(request.POST, instance=reservation)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.gestionnaire = request.user
            reservation.save()
            
            messages.success(request, f'Réservation {reservation.client.prenom} {reservation.client.nom} modifiée avec succès !')
            return redirect('reservations:detail', pk=reservation.pk)
    else:
        form = ReservationForm(instance=reservation)
    
    context = {
        'form': form,
        'reservation': reservation,
        'titre': f'Modifier {reservation.client.prenom} {reservation.client.nom}',
        'action': 'Modifier'
    }
    return render(request, 'reservations/modifier_reservation.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def annuler_reservation(request, pk):
    """Annuler une réservation selon cahier"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    if request.method == 'POST':
        reservation.annuler()
        messages.success(request, f'Réservation {reservation.client.prenom} {reservation.client.nom} annulée avec succès !')
        return redirect('reservations:liste')
    
    context = {
        'reservation': reservation,
        'titre': f'Annuler {reservation.client.prenom} {reservation.client.nom}',
    }
    return render(request, 'reservations/annuler_reservation.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def verifier_disponibilite(request):
    """Vérifier la disponibilité d'une réservation selon cahier"""
    if request.method == 'POST':
        reservation_id = request.POST.get('reservation_id')
        if not reservation_id:
            messages.error(request, 'Veuillez sélectionner une réservation')
            return redirect('reservations:liste')
        
        reservation = get_object_or_404(Reservation, pk=reservation_id)
        
        # Vérifier la disponibilité selon cahier
        try:
            disponible = reservation.verifier_disponibilite()
        except ValidationError as e:
            messages.error(request, e)
            return redirect('reservations:liste')
        
        if disponible:
            messages.success(request, f'Réservation {reservation.client.prenom} {reservation.client.nom} disponible !')
        else:
            messages.error(request, f'Réservation {reservation.client.prenom} {reservation.client.nom} indisponible !')
        
        return redirect('reservations:liste')
    else:
        messages.error(request, 'Veuillez utiliser le formulaire de recherche.')
        return redirect('reservations:liste')

@login_required
@user_passes_test(is_gestionnaire)
def arrivees_du_jour(request):
    """Réservations arrivées du jour selon cahier"""
    from apps.appartements.models import Appartement
    appartements = Appartement.objects.all()
    
    context = {
        'appartements': appartements,
    }
    return render(request, 'reservations/arrivees_du_jour.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def departs_du_jour(request):
    """Réservations départs du jour selon cahier"""
    from apps.appartements.models import Appartement
    appartements = Appartement.objects.all()
    
    context = {
        'appartements': appartements,
    }
    return render(request, 'reservations/departs_du_jour.html', context)
