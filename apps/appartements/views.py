# ==========================================
# apps/appartements/views.py - Gestion appartements
# ==========================================
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q

from apps.notifications.services import NotificationService
from apps.users.views import is_gestionnaire
from .models import Appartement, PhotoAppartement
from apps.appartements.forms import AppartementForm, PhotoAppartementForm

@login_required
@user_passes_test(is_gestionnaire)
def liste_appartements(request):
    """Liste des appartements avec filtres selon cahier"""
    appartements = Appartement.objects.all().prefetch_related('photos')
    
    # Filtres simples
    statut_filtre = request.GET.get('statut')
    type_filtre = request.GET.get('type')
    recherche = request.GET.get('q')
    
    if statut_filtre:
        appartements = appartements.filter(statut=statut_filtre)
    if type_filtre:
        appartements = appartements.filter(type_logement=type_filtre)
    if recherche:
        appartements = appartements.filter(
            Q(numero__icontains=recherche) | 
            Q(maison__icontains=recherche)
        )
    
    context = {
        'appartements': appartements,
        'statuts': Appartement.STATUT_CHOICES,
        'types': Appartement.TYPE_CHOICES,
        'statut_filtre': statut_filtre,
        'type_filtre': type_filtre,
        'recherche': recherche,
    }
    return render(request, 'appartements/liste.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def detail_appartement(request, pk):
    """Détail d'un appartement selon cahier"""
    appartement = get_object_or_404(Appartement, pk=pk)
    
    # Réservations en cours et à venir
    from apps.reservations.models import Reservation
    reservations = Reservation.objects.filter(
        appartement=appartement,
        date_depart__gte=timezone.now().date()
    ).order_by('date_arrivee')[:5]
    
    # Inventaire
    from apps.inventaire.models import EquipementAppartement
    equipements = EquipementAppartement.objects.filter(appartement=appartement)
    valeur_totale = sum(eq.prix_achat for eq in equipements)
    
    context = {
        'appartement': appartement,
        'reservations': reservations,
        'equipements': equipements,
        'valeur_totale': valeur_totale,
    }
    return render(request, 'appartements/detail.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def creer_appartement(request):
    """Créer un appartement en moins de 2 minutes selon cahier"""
    if request.method == 'POST':
        form = AppartementForm(request.POST)
        if form.is_valid():
            appartement = form.save()

            # Notification pour les gestionnaires
            NotificationService.notify_appartement_created(appartement, request.user)
            messages.success(request, f'Appartement {appartement.numero} créé avec succès !')
            return redirect('appartements:detail', pk=appartement.pk)
    else:
        form = AppartementForm()
    
    return render(request, 'appartements/formulaire.html', {
        'form': form,
        'titre': 'Nouveau Appartement',
        'action': 'Créer'
    })

@login_required
@user_passes_test(is_gestionnaire)
def modifier_appartement(request, pk):
    """Modifier un appartement"""
    appartement = get_object_or_404(Appartement, pk=pk)
    
    if request.method == 'POST':
        form = AppartementForm(request.POST, instance=appartement)
        if form.is_valid():
            form.save()
            # Notification pour les gestionnaires
            NotificationService.notify_appartement_updated(appartement, request.user)
            messages.success(request, f'Appartement {appartement.numero} modifié avec succès !')
            return redirect('appartements:detail', pk=appartement.pk)
    else:
        form = AppartementForm(instance=appartement)
    
    return render(request, 'appartements/formulaire.html', {
        'form': form,
        'appartement': appartement,
        'titre': f'Modifier {appartement.numero}',
        'action': 'Modifier'
    })

@login_required
@user_passes_test(is_gestionnaire)
def changer_statut_appartement(request, pk):
    """Changer statut en 1 clic selon cahier"""
    appartement = get_object_or_404(Appartement, pk=pk)
    nouveau_statut = request.GET.get('statut')
    
    if nouveau_statut in dict(Appartement.STATUT_CHOICES):
        appartement.statut = nouveau_statut
        appartement.save()
        # Notification pour les gestionnaires
        NotificationService.notify_appartement_updated(appartement, request.user)
        messages.success(request, f'Statut de {appartement.numero} changé en {appartement.get_statut_display()}')
    
    return redirect('appartements:liste')

#gerer photos
@login_required
@user_passes_test(is_gestionnaire)
def gerer_photos(request):  
    """Gestion des photos selon cahier"""
    appartements = Appartement.objects.all()
    
    context = {
        'appartements': appartements,
        'photos': [appartement.photos.all() for appartement in appartements],
    }
    return render(request, 'appartements/gerer_photo.html', context)


@login_required
@user_passes_test(is_gestionnaire)
def ajouter_photo(request, pk=None):
    if pk:
        appartement = get_object_or_404(Appartement, pk=pk)
    
        if request.method == 'POST':
            form = PhotoAppartementForm(request.POST, request.FILES)
            if form.is_valid():
                photo = form.save(commit=False)
                photo.appartement = appartement
                photo.save()
                
                messages.success(request, f'Photo ajoutée avec succès !')
                return redirect('appartements:photos')
        else:
            form = PhotoAppartementForm()
        
        context = {
            'form': form,
            'appartement': appartement,
            'titre': f'Ajouter une photo - {appartement.numero}',
        }
        return render(request, 'appartements/ajouter_photo.html', context)
    else:
        messages.error(request, 'Veuillez sélectionner un appartement')
        return redirect('appartements:liste')

@login_required
@user_passes_test(is_gestionnaire)
def supprimer_photo(request, photo_pk):
    """Supprimer une photo selon cahier"""
    photo = get_object_or_404(PhotoAppartement, pk=photo_pk)
    
    if request.method == 'POST':
        photo.delete()
        # Notification pour les gestionnaires
        NotificationService.notify_photo_deleted(photo, request.user)
        messages.success(request, f'Photo supprimée avec succès !')
        return redirect('appartements:photos')
    
    context = {
        'photo': photo,
        'titre': f'Supprimer {photo.nom_piece}',
    }
    return render(request, 'appartements/supprimer_photo.html', context)