# home/admin_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.urls import reverse
from .models import Ville, CategorieMaison, Maison, PhotoMaison, Reservation
from .forms import (
    VilleForm, CategorieMaisonForm, MaisonForm, 
    PhotoMaisonForm, ReservationForm, MaisonFilterForm
)

def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Tableau de bord principal de l'administration"""
    
    # Statistiques
    stats = {
        'total_maisons': Maison.objects.count(),
        'maisons_disponibles': Maison.objects.filter(disponible=True).count(),
        'maisons_featured': Maison.objects.filter(featured=True).count(),
        'total_villes': Ville.objects.count(),
        'total_categories': CategorieMaison.objects.count(),
        'total_reservations': Reservation.objects.count(),
        'reservations_en_attente': Reservation.objects.filter(statut='en_attente').count(),
        'reservations_confirmees': Reservation.objects.filter(statut='confirmee').count(),
    }
    
    # Dernières maisons ajoutées
    dernieres_maisons = Maison.objects.select_related('ville', 'categorie').order_by('-date_creation')[:5]
    
    # Dernières réservations
    dernieres_reservations = Reservation.objects.select_related('maison', 'locataire').order_by('-date_creation')[:5]
    
    # Maisons populaires (plus de réservations)
    maisons_populaires = Maison.objects.annotate(
        nb_reservations=Count('reservation')
    ).order_by('-nb_reservations')[:5]
    
    context = {
        'stats': stats,
        'dernieres_maisons': dernieres_maisons,
        'dernieres_reservations': dernieres_reservations,
        'maisons_populaires': maisons_populaires,
    }
    
    return render(request, 'admin/dashboard.html', context)

# ======== GESTION DES VILLES ========

@login_required
@user_passes_test(is_admin)
def admin_villes_list(request):
    """Liste des villes"""
    search = request.GET.get('search', '')
    villes = Ville.objects.annotate(nb_maisons=Count('maison'))
    
    if search:
        villes = villes.filter(
            Q(nom__icontains=search) | 
            Q(departement__icontains=search) | 
            Q(code_postal__icontains=search)
        )
    
    villes = villes.order_by('nom')
    
    paginator = Paginator(villes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
    }
    
    return render(request, 'admin/villes/list.html', context)

@login_required
@user_passes_test(is_admin)
def admin_ville_create(request):
    """Créer une nouvelle ville"""
    if request.method == 'POST':
        form = VilleForm(request.POST)
        if form.is_valid():
            ville = form.save()
            messages.success(request, f'La ville "{ville.nom}" a été créée avec succès.')
            return redirect('admin_villes_list')
    else:
        form = VilleForm()
    
    context = {'form': form, 'action': 'Créer'}
    return render(request, 'admin/villes/form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_ville_edit(request, pk):
    """Modifier une ville"""
    ville = get_object_or_404(Ville, pk=pk)
    
    if request.method == 'POST':
        form = VilleForm(request.POST, instance=ville)
        if form.is_valid():
            form.save()
            messages.success(request, f'La ville "{ville.nom}" a été modifiée avec succès.')
            return redirect('admin_villes_list')
    else:
        form = VilleForm(instance=ville)
    
    context = {'form': form, 'action': 'Modifier', 'objet': ville}
    return render(request, 'admin/villes/form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_ville_delete(request, pk):
    """Supprimer une ville"""
    ville = get_object_or_404(Ville, pk=pk)
    
    if request.method == 'POST':
        nom = ville.nom
        ville.delete()
        messages.success(request, f'La ville "{nom}" a été supprimée avec succès.')
        return redirect('admin_villes_list')
    
    context = {'objet': ville, 'type': 'ville'}
    return render(request, 'admin/confirm_delete.html', context)

# ======== GESTION DES CATÉGORIES ========

@login_required
@user_passes_test(is_admin)
def admin_categories_list(request):
    """Liste des catégories"""
    categories = CategorieMaison.objects.annotate(nb_maisons=Count('maison')).order_by('nom')
    
    context = {'categories': categories}
    return render(request, 'admin/categories/list.html', context)

@login_required
@user_passes_test(is_admin)
def admin_categorie_create(request):
    """Créer une nouvelle catégorie"""
    if request.method == 'POST':
        form = CategorieMaisonForm(request.POST)
        if form.is_valid():
            categorie = form.save()
            messages.success(request, f'La catégorie "{categorie.nom}" a été créée avec succès.')
            return redirect('admin_categories_list')
    else:
        form = CategorieMaisonForm()
    
    context = {'form': form, 'action': 'Créer'}
    return render(request, 'admin/categories/form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_categorie_edit(request, pk):
    """Modifier une catégorie"""
    categorie = get_object_or_404(CategorieMaison, pk=pk)
    
    if request.method == 'POST':
        form = CategorieMaisonForm(request.POST, instance=categorie)
        if form.is_valid():
            form.save()
            messages.success(request, f'La catégorie "{categorie.nom}" a été modifiée avec succès.')
            return redirect('admin_categories_list')
    else:
        form = CategorieMaisonForm(instance=categorie)
    
    context = {'form': form, 'action': 'Modifier', 'objet': categorie}
    return render(request, 'admin/categories/form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_categorie_delete(request, pk):
    """Supprimer une catégorie"""
    categorie = get_object_or_404(CategorieMaison, pk=pk)
    
    if request.method == 'POST':
        nom = categorie.nom
        categorie.delete()
        messages.success(request, f'La catégorie "{nom}" a été supprimée avec succès.')
        return redirect('admin_categories_list')
    
    context = {'objet': categorie, 'type': 'catégorie'}
    return render(request, 'admin/confirm_delete.html', context)

# ======== GESTION DES MAISONS ========

@login_required
@user_passes_test(is_admin)
def admin_maisons_list(request):
    """Liste des maisons avec filtres"""
    form = MaisonFilterForm(request.GET)
    maisons = Maison.objects.select_related('ville', 'categorie', 'proprietaire')
    
    if form.is_valid():
        search = form.cleaned_data.get('search')
        ville = form.cleaned_data.get('ville')
        categorie = form.cleaned_data.get('categorie')
        disponible = form.cleaned_data.get('disponible')
        featured = form.cleaned_data.get('featured')
        
        if search:
            maisons = maisons.filter(
                Q(nom__icontains=search) |
                Q(description__icontains=search) |
                Q(adresse__icontains=search)
            )
        
        if ville:
            maisons = maisons.filter(ville=ville)
        
        if categorie:
            maisons = maisons.filter(categorie=categorie)
        
        if disponible:
            maisons = maisons.filter(disponible=disponible == 'True')
        
        if featured:
            maisons = maisons.filter(featured=featured == 'True')
    
    maisons = maisons.order_by('-date_creation')
    
    paginator = Paginator(maisons, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
    }
    
    return render(request, 'admin/maisons/list.html', context)

@login_required
@user_passes_test(is_admin)
def admin_maison_create(request):
    """Créer une nouvelle maison"""
    if request.method == 'POST':
        form = MaisonForm(request.POST)
        if form.is_valid():
            maison = form.save()
            messages.success(request, f'La maison "{maison.nom}" a été créée avec succès.')
            return redirect('admin_maisons_list')
    else:
        form = MaisonForm()
    
    context = {'form': form, 'action': 'Créer'}
    return render(request, 'admin/maisons/form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_maison_edit(request, pk):
    """Modifier une maison"""
    maison = get_object_or_404(Maison, pk=pk)
    
    if request.method == 'POST':
        form = MaisonForm(request.POST, instance=maison)
        if form.is_valid():
            form.save()
            messages.success(request, f'La maison "{maison.nom}" a été modifiée avec succès.')
            return redirect('admin_maisons_list')
    else:
        form = MaisonForm(instance=maison)
    
    context = {'form': form, 'action': 'Modifier', 'objet': maison}
    return render(request, 'admin/maisons/form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_maison_delete(request, pk):
    """Supprimer une maison"""
    maison = get_object_or_404(Maison, pk=pk)
    
    if request.method == 'POST':
        nom = maison.nom
        maison.delete()
        messages.success(request, f'La maison "{nom}" a été supprimée avec succès.')
        return redirect('admin_maisons_list')
    
    context = {'objet': maison, 'type': 'maison'}
    return render(request, 'admin/confirm_delete.html', context)

# ======== GESTION DES PHOTOS ========

@login_required
@user_passes_test(is_admin)
def admin_photos_list(request):
    """Liste des photos"""
    maison_id = request.GET.get('maison')
    photos = PhotoMaison.objects.select_related('maison')
    
    if maison_id:
        photos = photos.filter(maison_id=maison_id)
    
    photos = photos.order_by('maison__nom', 'ordre')
    
    paginator = Paginator(photos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    maisons = Maison.objects.all().order_by('nom')
    
    context = {
        'page_obj': page_obj,
        'maisons': maisons,
        'maison_selectionnee': maison_id,
    }
    
    return render(request, 'admin/photos/list.html', context)

@login_required
@user_passes_test(is_admin)
def admin_photo_create(request):
    """Ajouter une nouvelle photo"""
    if request.method == 'POST':
        form = PhotoMaisonForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save()
            messages.success(request, f'Photo ajoutée avec succès pour "{photo.maison.nom}".')
            return redirect('admin_photos_list')
    else:
        form = PhotoMaisonForm()
    
    context = {'form': form, 'action': 'Ajouter'}
    return render(request, 'admin/photos/form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_photo_edit(request, pk):
    """Modifier une photo"""
    photo = get_object_or_404(PhotoMaison, pk=pk)
    
    if request.method == 'POST':
        form = PhotoMaisonForm(request.POST, request.FILES, instance=photo)
        if form.is_valid():
            form.save()
            messages.success(request, f'Photo modifiée avec succès.')
            return redirect('admin_photos_list')
    else:
        form = PhotoMaisonForm(instance=photo)
    
    context = {'form': form, 'action': 'Modifier', 'objet': photo}
    return render(request, 'admin/photos/form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_photo_delete(request, pk):
    """Supprimer une photo"""
    photo = get_object_or_404(PhotoMaison, pk=pk)
    
    if request.method == 'POST':
        photo.delete()
        messages.success(request, f'Photo supprimée avec succès.')
        return redirect('admin_photos_list')
    
    context = {'objet': photo, 'type': 'photo'}
    return render(request, 'admin/confirm_delete.html', context)

# ======== GESTION DES RÉSERVATIONS ========

@login_required
@user_passes_test(is_admin)
def admin_reservations_list(request):
    """Liste des réservations"""
    statut = request.GET.get('statut', '')
    search = request.GET.get('search', '')
    
    reservations = Reservation.objects.select_related('maison', 'locataire')
    
    if statut:
        reservations = reservations.filter(statut=statut)
    
    if search:
        reservations = reservations.filter(
            Q(maison__nom__icontains=search) |
            Q(locataire__username__icontains=search) |
            Q(locataire__email__icontains=search)
        )
    
    reservations = reservations.order_by('-date_creation')
    
    paginator = Paginator(reservations, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'statut_actuel': statut,
        'search': search,
        'statuts': Reservation.STATUT_CHOICES,
    }
    
    return render(request, 'admin/reservations/list.html', context)

@login_required
@user_passes_test(is_admin)
def admin_reservation_create(request):
    """Créer une nouvelle réservation"""
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save()
            messages.success(request, f'Réservation créée avec succès.')
            return redirect('admin_reservations_list')
    else:
        form = ReservationForm()
    
    context = {'form': form, 'action': 'Créer'}
    return render(request, 'admin/reservations/form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_reservation_edit(request, pk):
    """Modifier une réservation"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    if request.method == 'POST':
        form = ReservationForm(request.POST, instance=reservation)
        if form.is_valid():
            form.save()
            messages.success(request, f'Réservation modifiée avec succès.')
            return redirect('admin_reservations_list')
    else:
        form = ReservationForm(instance=reservation)
    
    context = {'form': form, 'action': 'Modifier', 'objet': reservation}
    return render(request, 'admin/reservations/form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_reservation_delete(request, pk):
    """Supprimer une réservation"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    if request.method == 'POST':
        reservation.delete()
        messages.success(request, f'Réservation supprimée avec succès.')
        return redirect('admin_reservations_list')
    
    context = {'objet': reservation, 'type': 'réservation'}
    return render(request, 'admin/confirm_delete.html', context)