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
    """Liste des appartements avec filtres et statistiques selon cahier"""
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
    
    # AJOUT : Calcul des statistiques par statut
    from django.db.models import Count
    stats_statut = Appartement.objects.values('statut').annotate(
        count=Count('id')
    ).order_by('statut')
    
    # Convertir en dictionnaire pour faciliter l'accès
    stats = {
        'disponible': 0,
        'occupe': 0,
        'maintenance': 0,
        'total': Appartement.objects.count()
    }
    
    for stat in stats_statut:
        stats[stat['statut']] = stat['count']
    
    # AJOUT : Statistiques par type
    stats_type = Appartement.objects.values('type_logement').annotate(
        count=Count('id')
    ).order_by('type_logement')
    
    stats_types = {
        'studio': 0,
        't1': 0,
        't2': 0
    }
    
    for stat in stats_type:
        stats_types[stat['type_logement']] = stat['count']
    
    # AJOUT : Revenus moyens par appartement
    from apps.reservations.models import Reservation
    from django.utils import timezone
    from django.db.models import Avg, Sum
    
    mois_actuel = timezone.now().month
    annee_actuelle = timezone.now().year
    
    revenus_mois = Reservation.objects.filter(
        statut__in=['confirmee', 'en_cours', 'terminee'],
        date_arrivee__month=mois_actuel,
        date_arrivee__year=annee_actuelle
    ).aggregate(
        total=Sum('prix_total'),
        moyenne=Avg('prix_total')
    )
    
    context = {
        'appartements': appartements,
        'statuts': Appartement.STATUT_CHOICES,
        'types': Appartement.TYPE_CHOICES,
        'statut_filtre': statut_filtre,
        'type_filtre': type_filtre,
        'recherche': recherche,
        # AJOUT : Statistiques
        'stats': stats,
        'stats_types': stats_types,
        'revenus_mois': revenus_mois.get('total') or 0,
        'revenus_moyenne': revenus_mois.get('moyenne') or 0,
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