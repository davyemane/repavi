# ==========================================
# apps/reservations/views.py - Réservations et planning CORRIGÉ
# ==========================================
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta, date

from apps.users.views import is_gestionnaire
from .models import Reservation
from .forms import ReservationForm

@login_required
@user_passes_test(is_gestionnaire)
def calendrier_reservations(request):
    """Vue mensuelle avec couleurs par statut selon cahier"""
    import calendar
    
    # Mois en cours par défaut
    annee = int(request.GET.get('annee', datetime.now().year))
    mois = int(request.GET.get('mois', datetime.now().month))
    
    # Premier et dernier jour du mois
    premier_jour = datetime(annee, mois, 1).date()
    if mois == 12:
        dernier_jour = datetime(annee + 1, 1, 1).date() - timedelta(days=1)
    else:
        dernier_jour = datetime(annee, mois + 1, 1).date() - timedelta(days=1)
    
    # Générer les jours du mois
    cal = calendar.monthcalendar(annee, mois)
    jours_mois = []
    for semaine in cal:
        for jour in semaine:
            if jour != 0:
                jours_mois.append(datetime(annee, mois, jour).date())
    
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
        
        # Organiser les réservations par jour
        jours_data = []
        for jour in jours_mois:
            reservations_jour = []
            for reservation in app_reservations:
                if reservation.date_arrivee <= jour < reservation.date_depart:
                    reservations_jour.append(reservation)
            jours_data.append({
                'date': jour,
                'reservations': reservations_jour
            })
        
        calendrier_data.append({
            'appartement': appartement,
            'jours': jours_data
        })
    
    # Arrivées du jour
    arrivees_aujourd_hui = Reservation.objects.filter(
        date_arrivee=date.today(),
        statut='confirmee'
    ).select_related('client', 'appartement')
    
    context = {
        'calendrier_data': calendrier_data,
        'jours_mois': jours_mois,
        'annee': annee,
        'mois': mois,
        'mois_nom': datetime(annee, mois, 1).strftime('%B %Y'),
        'premier_jour': premier_jour,
        'dernier_jour': dernier_jour,
        'arrivees_aujourd_hui': arrivees_aujourd_hui,
        'calendrier_html': cal,
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
                
                # Calculs automatiques AVANT sauvegarde
                if reservation.date_arrivee and reservation.date_depart and reservation.appartement:
                    reservation.nombre_nuits = (reservation.date_depart - reservation.date_arrivee).days
                    reservation.prix_total = reservation.nombre_nuits * reservation.appartement.prix_par_nuit
                
                # Sauvegarde avec validation
                reservation.save()
                
                # Créer l'échéancier de paiement automatiquement
                from .services import ReservationService
                ReservationService.creer_echeancier(reservation)
                
                messages.success(request, f'Réservation créée avec succès ! Échéancier généré automatiquement.')
                return redirect('reservations:detail', pk=reservation.pk)
                
            except ValidationError as e:
                if hasattr(e, 'messages'):
                    for error in e.messages:
                        messages.error(request, error)
                else:
                    messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Erreur lors de la création : {str(e)}')
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

@login_required
@user_passes_test(is_gestionnaire)
def liste_reservations(request):
    """Liste des réservations selon cahier"""
    statut_filtre = request.GET.get('statut', 'tous')
    
    reservations = Reservation.objects.select_related(
        'client', 'appartement'
    ).order_by('-date_arrivee')
    
    if statut_filtre != 'tous':
        reservations = reservations.filter(statut=statut_filtre)
    
    context = {
        'reservations': reservations,
        'statut_filtre': statut_filtre,
    }
    return render(request, 'reservations/liste.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def detail_reservation(request, pk):
    """Détail d'une réservation selon cahier"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    # Récupérer l'échéancier de paiement - CORRECTION
    try:
        from apps.paiements.models import EcheancierPaiement
        echeanciers = EcheancierPaiement.objects.filter(
            reservation=reservation
        ).order_by('date_echeance')
    except ImportError:
        # Si le modèle n'existe pas encore
        echeanciers = []
    
    context = {
        'reservation': reservation,
        'echeanciers': echeanciers,
    }        
    return render(request, 'reservations/detail.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def modifier_reservation(request, pk):
    """Modifier une réservation selon cahier"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    if request.method == 'POST':
        form = ReservationForm(request.POST, instance=reservation)
        if form.is_valid():
            try:
                reservation = form.save(commit=False)
                reservation.gestionnaire = request.user
                reservation.full_clean()
                reservation.save()
                
                messages.success(request, f'Réservation modifiée avec succès !')
                return redirect('reservations:detail', pk=reservation.pk)
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
    else:
        form = ReservationForm(instance=reservation)
    
    context = {
        'form': form,
        'reservation': reservation,
        'titre': f'Modifier la réservation',
        'action': 'Modifier'
    }
    return render(request, 'reservations/formulaire.html', context)


@login_required
@user_passes_test(is_gestionnaire)
def arrivees_du_jour(request):
    """Arrivées du jour selon cahier"""
    arrivees = Reservation.objects.filter(
        date_arrivee=date.today(),
        statut='confirmee'
    ).select_related('client', 'appartement')
    
    context = {
        'arrivees': arrivees,
        'date_jour': date.today(),
    }
    return render(request, 'reservations/arrivees_jour.html', context)

@login_required  
@user_passes_test(is_gestionnaire)
def departs_du_jour(request):
    """Départs du jour selon cahier"""
    departs = Reservation.objects.filter(
        date_depart=date.today(),
        statut='en_cours'
    ).select_related('client', 'appartement')
    
    context = {
        'departs': departs,
        'date_jour': date.today(),
    }
    return render(request, 'reservations/departs_jour.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def annuler_reservation(request, pk):
    """Annuler une réservation avec log"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    if request.method == 'POST':
        # Sauvegarder infos pour log
        client_nom = f"{reservation.client.nom} {reservation.client.prenom}"
        
        reservation.statut = 'annulee'
        reservation.save()
        
        # Log manuel de l'annulation
        from apps.users.models import ActionLog
        ActionLog.objects.create(
            utilisateur=request.user,
            action='update',
            model_name='Reservation',
            object_id=str(reservation.pk),
            object_repr=f"Annulation réservation {client_nom}",
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            url=request.get_full_path(),
            method=request.method,
            details='{"action_type": "cancellation"}'
        )
        
        messages.success(request, f'Réservation de {client_nom} annulée avec succès !')
        return redirect('reservations:liste')
    
    return render(request, 'reservations/annuler.html', {'reservation': reservation})

@login_required
@user_passes_test(is_gestionnaire)
def supprimer_reservation(request, pk):
    """Supprimer réservation avec log détaillé"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    if request.method == 'POST':
        # Infos pour log
        client_nom = f"{reservation.client.nom} {reservation.client.prenom}"
        appartement_num = reservation.appartement.numero
        montant = reservation.prix_total
        
        # Log avant suppression
        from apps.users.models import ActionLog
        ActionLog.objects.create(
            utilisateur=request.user,
            action='delete',
            model_name='Reservation',
            object_id=str(reservation.pk),
            object_repr=f"Suppression réservation {client_nom} - Apt {appartement_num}",
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            url=request.get_full_path(),
            method=request.method,
            details=f'{{"client": "{client_nom}", "appartement": "{appartement_num}", "montant": {montant}}}'
        )
        
        reservation.delete()
        
        messages.success(request, f'Réservation supprimée définitivement.')
        return redirect('reservations:liste')
    
    return render(request, 'reservations/confirmer_suppression.html', {'reservation': reservation})

def get_client_ip(request):
    """Helper pour IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')