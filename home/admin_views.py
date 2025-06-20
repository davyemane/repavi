# À ajouter en haut de votre home/admin_views.py (remplacer les imports existants)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.urls import reverse

# Import sécurisé des décorateurs
try:
    from utils.decorators import gestionnaire_required, super_admin_required, role_required
except ImportError:
    # Fallback si les décorateurs n'existent pas
    def gestionnaire_required(func):
        return login_required(func)
    def super_admin_required(func):
        return login_required(func)
    def role_required(roles):
        def decorator(func):
            return login_required(func)
        return decorator

# Import sécurisé des services
try:
    from services.maison_service import MaisonService
    from services.photo_service import PhotoService
    from services.reservation_service import ReservationService
    from services.statistics_service import StatisticsService
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False
    print("⚠️ Services non disponibles")

from .models import Ville, CategorieMaison, Maison, PhotoMaison, Reservation
from .forms import (
    VilleForm, CategorieMaisonForm, MaisonForm, 
    PhotoMaisonForm, ReservationForm, MaisonFilterForm
)


@login_required
@gestionnaire_required
def admin_dashboard(request):
    """Tableau de bord principal de l'administration - ADAPTÉ"""
    
    # Utiliser le service de statistiques
    stats = StatisticsService.get_dashboard_stats(request.user)
    
    # Dernières maisons ajoutées (selon les permissions)
    dernieres_maisons = MaisonService.get_maisons_for_user(request.user)[:5]
    
    # Dernières réservations (selon les permissions)
    dernieres_reservations = ReservationService.get_reservations_for_user(request.user)[:5]
    
    # Maisons populaires (plus de réservations)
    if request.user.is_super_admin():
        maisons_populaires = Maison.objects.annotate(
            nb_reservations=Count('reservations')
        ).order_by('-nb_reservations')[:5]
    else:
        maisons_populaires = Maison.objects.filter(
            gestionnaire=request.user
        ).annotate(
            nb_reservations=Count('reservations')
        ).order_by('-nb_reservations')[:5]
    
    context = {
        'stats': stats,
        'dernieres_maisons': dernieres_maisons,
        'dernieres_reservations': dernieres_reservations,
        'maisons_populaires': maisons_populaires,
        'user_role': request.user.role,
        'is_gestionnaire': request.user.is_gestionnaire(),
        'is_super_admin': request.user.is_super_admin(),
    }
    
    return render(request, 'admin/dashboard.html', context)

# ======== GESTION DES VILLES ========

@login_required
@gestionnaire_required
def admin_villes_list(request):
    """Liste des villes - ADAPTÉ"""
    search = request.GET.get('search', '')
    villes = Ville.objects.annotate(nb_maisons=Count('maison'))
    
    # Filtrer selon les permissions
    if not request.user.is_super_admin():
        villes = villes.filter(maison__gestionnaire=request.user).distinct()
    
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
        'can_create': request.user.has_gestionnaire_permissions(),
    }
    
    return render(request, 'admin/villes/list.html', context)

@login_required
@gestionnaire_required
def admin_ville_create(request):
    """Créer une nouvelle ville - ADAPTÉ"""
    if request.method == 'POST':
        form = VilleForm(request.POST)
        if form.is_valid():
            ville = form.save()
            messages.success(request, f'La ville "{ville.nom}" a été créée avec succès.')
            return redirect('repavi_admin:villes_list')
    else:
        form = VilleForm()
    
    context = {'form': form, 'action': 'Créer'}
    return render(request, 'admin/villes/form.html', context)

@login_required
@gestionnaire_required
def admin_ville_edit(request, pk):
    """Modifier une ville - ADAPTÉ"""
    ville = get_object_or_404(Ville, pk=pk)
    
    # Vérifier les permissions
    if not request.user.is_super_admin():
        if not ville.maison_set.filter(gestionnaire=request.user).exists():
            messages.error(request, "Vous n'avez pas les droits pour modifier cette ville.")
            return redirect('repavi_admin:villes_list')
    
    if request.method == 'POST':
        form = VilleForm(request.POST, instance=ville)
        if form.is_valid():
            form.save()
            messages.success(request, f'La ville "{ville.nom}" a été modifiée avec succès.')
            return redirect('repavi_admin:villes_list')
    else:
        form = VilleForm(instance=ville)
    
    context = {'form': form, 'action': 'Modifier', 'objet': ville}
    return render(request, 'admin/villes/form.html', context)

@login_required
@super_admin_required
def admin_ville_delete(request, pk):
    """Supprimer une ville - SUPER ADMIN SEULEMENT"""
    ville = get_object_or_404(Ville, pk=pk)
    
    if request.method == 'POST':
        nom = ville.nom
        ville.delete()
        messages.success(request, f'La ville "{nom}" a été supprimée avec succès.')
        return redirect('repavi_admin:villes_list')
    
    context = {'objet': ville, 'type': 'ville'}
    return render(request, 'admin/confirm_delete.html', context)

# ======== GESTION DES CATÉGORIES ========

@login_required
@gestionnaire_required
def admin_categories_list(request):
    """Liste des catégories - ADAPTÉ"""
    categories = CategorieMaison.objects.annotate(nb_maisons=Count('maison'))
    
    # Filtrer selon les permissions pour gestionnaires
    if not request.user.is_super_admin():
        categories = categories.filter(maison__gestionnaire=request.user).distinct()
    
    categories = categories.order_by('nom')
    
    context = {
        'categories': categories,
        'can_create': request.user.has_gestionnaire_permissions(),
        'can_delete': request.user.is_super_admin(),
    }
    return render(request, 'admin/categories/list.html', context)

@login_required
@gestionnaire_required
def admin_categorie_create(request):
    """Créer une nouvelle catégorie"""
    if request.method == 'POST':
        form = CategorieMaisonForm(request.POST)
        if form.is_valid():
            categorie = form.save()
            messages.success(request, f'La catégorie "{categorie.nom}" a été créée avec succès.')
            return redirect('repavi_admin:categories_list')
    else:
        form = CategorieMaisonForm()
    
    context = {'form': form, 'action': 'Créer'}
    return render(request, 'admin/categories/form.html', context)

@login_required
@gestionnaire_required
def admin_categorie_edit(request, pk):
    """Modifier une catégorie"""
    categorie = get_object_or_404(CategorieMaison, pk=pk)
    
    if request.method == 'POST':
        form = CategorieMaisonForm(request.POST, instance=categorie)
        if form.is_valid():
            form.save()
            messages.success(request, f'La catégorie "{categorie.nom}" a été modifiée avec succès.')
            return redirect('repavi_admin:categories_list')
    else:
        form = CategorieMaisonForm(instance=categorie)
    
    context = {'form': form, 'action': 'Modifier', 'objet': categorie}
    return render(request, 'admin/categories/form.html', context)

@login_required
@super_admin_required
def admin_categorie_delete(request, pk):
    """Supprimer une catégorie - SUPER ADMIN SEULEMENT"""
    categorie = get_object_or_404(CategorieMaison, pk=pk)
    
    if request.method == 'POST':
        nom = categorie.nom
        categorie.delete()
        messages.success(request, f'La catégorie "{nom}" a été supprimée avec succès.')
        return redirect('repavi_admin:categories_list')
    
    context = {'objet': categorie, 'type': 'catégorie'}
    return render(request, 'admin/confirm_delete.html', context)

# ======== GESTION DES MAISONS ========

@login_required
@gestionnaire_required
def admin_maisons_list(request):
    """Liste des maisons avec filtres - ADAPTÉ AVEC SERVICES"""
    form = MaisonFilterForm(request.GET)
    
    # Utiliser le service pour récupérer les maisons
    maisons = MaisonService.get_maisons_for_user(request.user)
    
    # Appliquer les filtres si le formulaire est valide
    if form.is_valid():
        search = form.cleaned_data.get('search')
        ville = form.cleaned_data.get('ville')
        categorie = form.cleaned_data.get('categorie')
        disponible = form.cleaned_data.get('disponible')
        featured = form.cleaned_data.get('featured')
        
        filters = {}
        if ville:
            filters['ville'] = ville
        if categorie:
            filters['categorie'] = categorie
        if disponible:
            filters['disponible'] = disponible == 'True'
        if featured:
            filters['featured'] = featured == 'True'
        
        # Utiliser le service de recherche
        maisons = MaisonService.search_maisons(search or '', request.user, filters)
    
    paginator = Paginator(maisons, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'can_create': request.user.has_gestionnaire_permissions(),
        'can_delete': request.user.is_super_admin(),
    }
    
    return render(request, 'admin/maisons/list.html', context)

@login_required
@gestionnaire_required
def admin_maison_create(request):
    """Créer une nouvelle maison - ADAPTÉ AVEC SERVICES"""
    if request.method == 'POST':
        form = MaisonForm(request.POST)
        if form.is_valid():
            try:
                data = form.cleaned_data
                # Le service gérera automatiquement le gestionnaire
                maison = MaisonService.create_maison(request.user, data)
                messages.success(request, f'La maison "{maison.nom}" a été créée avec succès.')
                return redirect('repavi_admin:maisons_list')
            except PermissionDenied as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Erreur lors de la création : {str(e)}')
    else:
        form = MaisonForm()
        # Pré-remplir le gestionnaire si pas super admin
        if not request.user.is_super_admin():
            form.fields['gestionnaire'].initial = request.user
            form.fields['gestionnaire'].widget = forms.HiddenInput()
    
    context = {'form': form, 'action': 'Créer'}
    return render(request, 'admin/maisons/form.html', context)

@login_required
@gestionnaire_required
def admin_maison_edit(request, pk):
    """Modifier une maison - ADAPTÉ AVEC SERVICES"""
    maison = get_object_or_404(Maison, pk=pk)
    
    # Vérifier les permissions via le modèle
    if not maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour modifier cette maison.")
        return redirect('repavi_admin:maisons_list')
    
    if request.method == 'POST':
        form = MaisonForm(request.POST, instance=maison)
        if form.is_valid():
            try:
                data = form.cleaned_data
                MaisonService.update_maison(request.user, maison, data)
                messages.success(request, f'La maison "{maison.nom}" a été modifiée avec succès.')
                return redirect('repavi_admin:maisons_list')
            except PermissionDenied as e:
                messages.error(request, str(e))
    else:
        form = MaisonForm(instance=maison)
        # Masquer le champ gestionnaire si pas super admin
        if not request.user.is_super_admin():
            form.fields['gestionnaire'].widget = forms.HiddenInput()
    
    context = {'form': form, 'action': 'Modifier', 'objet': maison}
    return render(request, 'admin/maisons/form.html', context)

@login_required
@gestionnaire_required
def admin_maison_delete(request, pk):
    """Supprimer une maison - ADAPTÉ AVEC SERVICES"""
    maison = get_object_or_404(Maison, pk=pk)
    
    if not maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour supprimer cette maison.")
        return redirect('repavi_admin:maisons_list')
    
    if request.method == 'POST':
        try:
            nom = maison.nom
            MaisonService.delete_maison(request.user, maison)
            messages.success(request, f'La maison "{nom}" a été supprimée avec succès.')
            return redirect('repavi_admin:maisons_list')
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('repavi_admin:maisons_list')
    
    context = {'objet': maison, 'type': 'maison'}
    return render(request, 'admin/confirm_delete.html', context)

# ======== GESTION DES PHOTOS ========

@login_required
@gestionnaire_required
def admin_photos_list(request):
    """Liste des photos - ADAPTÉ"""
    maison_id = request.GET.get('maison')
    photos = PhotoMaison.objects.select_related('maison')
    
    # Filtrer selon les permissions
    if not request.user.is_super_admin():
        photos = photos.filter(maison__gestionnaire=request.user)
    
    if maison_id:
        photos = photos.filter(maison_id=maison_id)
    
    photos = photos.order_by('maison__nom', 'ordre')
    
    paginator = Paginator(photos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Maisons disponibles selon les permissions
    if request.user.is_super_admin():
        maisons = Maison.objects.all()
    else:
        maisons = Maison.objects.filter(gestionnaire=request.user)
    
    context = {
        'page_obj': page_obj,
        'maisons': maisons.order_by('nom'),
        'maison_selectionnee': maison_id,
    }
    
    return render(request, 'admin/photos/list.html', context)

@login_required
@gestionnaire_required
def admin_photo_create(request):
    """Ajouter une nouvelle photo - ADAPTÉ AVEC SERVICES"""
    if request.method == 'POST':
        form = PhotoMaisonForm(request.POST, request.FILES)
        # Filtrer les maisons selon les permissions
        if not request.user.is_super_admin():
            form.fields['maison'].queryset = Maison.objects.filter(gestionnaire=request.user)
        
        if form.is_valid():
            try:
                maison = form.cleaned_data['maison']
                photo = PhotoService.upload_photo(
                    user=request.user,
                    maison=maison,
                    photo_data=form.cleaned_data['image'],
                    titre=form.cleaned_data.get('titre', ''),
                    principale=form.cleaned_data.get('principale', False),
                    ordre=form.cleaned_data.get('ordre', 0)
                )
                messages.success(request, f'Photo ajoutée avec succès pour "{photo.maison.nom}".')
                return redirect('repavi_admin:photos_list')
            except PermissionDenied as e:
                messages.error(request, str(e))
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = PhotoMaisonForm()
        # Filtrer les maisons disponibles
        if not request.user.is_super_admin():
            form.fields['maison'].queryset = Maison.objects.filter(gestionnaire=request.user)
    
    context = {'form': form, 'action': 'Ajouter'}
    return render(request, 'admin/photos/form.html', context)

@login_required
@gestionnaire_required
def admin_photo_edit(request, pk):
    """Modifier une photo - ADAPTÉ AVEC SERVICES"""
    photo = get_object_or_404(PhotoMaison, pk=pk)
    
    if not photo.maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour modifier cette photo.")
        return redirect('repavi_admin:photos_list')
    
    if request.method == 'POST':
        form = PhotoMaisonForm(request.POST, request.FILES, instance=photo)
        if form.is_valid():
            try:
                data = {
                    'titre': form.cleaned_data.get('titre'),
                    'principale': form.cleaned_data.get('principale'),
                    'ordre': form.cleaned_data.get('ordre')
                }
                PhotoService.update_photo(request.user, photo, data)
                messages.success(request, f'Photo modifiée avec succès.')
                return redirect('repavi_admin:photos_list')
            except PermissionDenied as e:
                messages.error(request, str(e))
    else:
        form = PhotoMaisonForm(instance=photo)
    
    context = {'form': form, 'action': 'Modifier', 'objet': photo}
    return render(request, 'admin/photos/form.html', context)

@login_required
@gestionnaire_required
def admin_photo_delete(request, pk):
    """Supprimer une photo - ADAPTÉ AVEC SERVICES"""
    photo = get_object_or_404(PhotoMaison, pk=pk)
    
    if not photo.maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour supprimer cette photo.")
        return redirect('repavi_admin:photos_list')
    
    if request.method == 'POST':
        try:
            PhotoService.delete_photo(request.user, photo)
            messages.success(request, f'Photo supprimée avec succès.')
            return redirect('repavi_admin:photos_list')
        except PermissionDenied as e:
            messages.error(request, str(e))
    
    context = {'objet': photo, 'type': 'photo'}
    return render(request, 'admin/confirm_delete.html', context)

# ======== GESTION DES RÉSERVATIONS ========

# À ajouter à la fin de votre home/admin_views.py existant

@login_required
@gestionnaire_required
def admin_reservation_create(request):
    """Créer une nouvelle réservation"""
    if request.method == 'POST':
        form = ReservationForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                # Version simple sans service pour éviter les erreurs
                reservation = form.save()
                messages.success(request, f'Réservation créée avec succès.')
                return redirect('repavi_admin:reservations_list')
            except Exception as e:
                messages.error(request, f'Erreur lors de la création : {str(e)}')
    else:
        form = ReservationForm(user=request.user)
    
    context = {'form': form, 'action': 'Créer'}
    return render(request, 'admin/reservations/form.html', context)


@login_required
@gestionnaire_required  
def admin_reservation_delete(request, pk):
    """Supprimer une réservation"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    if not reservation.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour supprimer cette réservation.")
        return redirect('repavi_admin:reservations_list')
    
    if request.method == 'POST':
        reservation.delete()
        messages.success(request, f'Réservation supprimée avec succès.')
        return redirect('repavi_admin:reservations_list')
    
    context = {'objet': reservation, 'type': 'réservation'}
    return render(request, 'admin/confirm_delete.html', context)

@login_required
@gestionnaire_required
def admin_reservations_list(request):
    """Liste des réservations - ADAPTÉ AVEC SERVICES"""
    statut = request.GET.get('statut', '')
    search = request.GET.get('search', '')
    
    # Utiliser le service pour récupérer les réservations selon les permissions
    reservations = ReservationService.get_reservations_for_user(request.user)
    
    if statut:
        reservations = reservations.filter(statut=statut)
    
    if search:
        reservations = reservations.filter(
            Q(maison__nom__icontains=search) |
            Q(client__username__icontains=search) |
            Q(client__email__icontains=search) |
            Q(client__first_name__icontains=search) |
            Q(client__last_name__icontains=search)
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
        'can_change_status': request.user.has_gestionnaire_permissions(),
    }
    
    return render(request, 'admin/reservations/list.html', context)

@login_required
@gestionnaire_required
def admin_reservation_edit(request, pk):
    """Modifier une réservation - ADAPTÉ"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    if not reservation.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour modifier cette réservation.")
        return redirect('repavi_admin:reservations_list')
    
    if request.method == 'POST':
        # Permettre seulement la modification du statut pour les gestionnaires
        nouveau_statut = request.POST.get('statut')
        if nouveau_statut and nouveau_statut in dict(Reservation.STATUT_CHOICES):
            try:
                ReservationService.update_reservation_status(
                    request.user, reservation, nouveau_statut
                )
                messages.success(request, f'Statut de la réservation mis à jour.')
                return redirect('repavi_admin:reservations_list')
            except PermissionDenied as e:
                messages.error(request, str(e))
    
    context = {
        'reservation': reservation,
        'statuts': Reservation.STATUT_CHOICES,
        'can_modify': reservation.can_be_managed_by(request.user),
    }
    
    return render(request, 'admin/reservations/edit.html', context)

