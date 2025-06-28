from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Case, When, IntegerField
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta

# Import sécurisé des décorateurs
try:
    from utils.decorators import gestionnaire_required, super_admin_required
except ImportError:
    def gestionnaire_required(func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Vous devez être connecté")
                return redirect('users:login')
            if not hasattr(request.user, 'is_gestionnaire') or not request.user.is_gestionnaire():
                messages.error(request, "Accès réservé aux gestionnaires")
                return redirect('home:index')
            return func(request, *args, **kwargs)
        return wrapper
        
    def super_admin_required(func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Vous devez être connecté")
                return redirect('users:login')
            if not hasattr(request.user, 'is_super_admin') or not request.user.is_super_admin():
                messages.error(request, "Accès réservé aux super administrateurs")
                return redirect('home:index')
            return func(request, *args, **kwargs)
        return wrapper

from .models import TypeMeuble, Meuble, HistoriqueEtatMeuble, PhotoMeuble, InventaireMaison
from .forms import MeubleForm, TypeMeubleForm, MeubleFilterForm, InventaireForm, PhotoMeubleForm
from home.models import Maison


# ======== DASHBOARD MEUBLES ========

@login_required
@gestionnaire_required
def meubles_dashboard(request):
    """Dashboard principal pour la gestion des meubles"""
    
    # Filtrer selon les permissions utilisateur
    if hasattr(request.user, 'is_super_admin') and request.user.is_super_admin():
        meubles = Meuble.objects.all()
        maisons = Maison.objects.all()
    else:
        meubles = Meuble.objects.filter(maison__gestionnaire=request.user)
        maisons = Maison.objects.filter(gestionnaire=request.user)
    
    # Statistiques générales
    stats = {
        'total_meubles': meubles.count(),
        'meubles_bon_etat': meubles.filter(etat='bon').count(),
        'meubles_defectueux': meubles.filter(etat='defectueux').count(),
        'meubles_usage': meubles.filter(etat='usage').count(),
        'meubles_hors_service': meubles.filter(etat='hors_service').count(),
        'total_maisons': maisons.count(),
        'total_types': TypeMeuble.objects.count(),
    }
    
    # Pourcentages
    if stats['total_meubles'] > 0:
        stats['pourcentage_bon_etat'] = round((stats['meubles_bon_etat'] / stats['total_meubles']) * 100, 1)
        stats['pourcentage_defectueux'] = round((stats['meubles_defectueux'] / stats['total_meubles']) * 100, 1)
    else:
        stats['pourcentage_bon_etat'] = 0
        stats['pourcentage_defectueux'] = 0
    
    # Meubles nécessitant une vérification
    meubles_a_verifier = meubles.filter(
        Q(date_derniere_verification__isnull=True) |
        Q(date_derniere_verification__lt=timezone.now().date() - timedelta(days=180))
    ).count()
    stats['meubles_a_verifier'] = meubles_a_verifier
    
    # Répartition par type de meuble
    repartition_types = meubles.values('type_meuble__nom').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Répartition par état
    repartition_etats = meubles.values('etat').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Meubles récemment ajoutés
    meubles_recents = meubles.select_related('maison', 'type_meuble').order_by('-date_creation')[:5]
    
    # Meubles nécessitant attention
    meubles_attention = meubles.filter(
        Q(etat='defectueux') |
        Q(date_derniere_verification__lt=timezone.now().date() - timedelta(days=180))
    ).select_related('maison', 'type_meuble')[:5]
    
    # Maisons avec le plus de meubles défectueux
    maisons_problemes = maisons.annotate(
        meubles_defectueux=Count('meubles', filter=Q(meubles__etat='defectueux'))
    ).filter(meubles_defectueux__gt=0).order_by('-meubles_defectueux')[:5]
    
    context = {
        'stats': stats,
        'repartition_types': repartition_types,
        'repartition_etats': repartition_etats,
        'meubles_recents': meubles_recents,
        'meubles_attention': meubles_attention,
        'maisons_problemes': maisons_problemes,
        'user_role': getattr(request.user, 'role', 'unknown'),
        'is_super_admin': hasattr(request.user, 'is_super_admin') and request.user.is_super_admin(),
    }
    
    return render(request, 'meubles/dashboard.html', context)


# ======== GESTION DES TYPES DE MEUBLES ========

@login_required
@gestionnaire_required
def types_meubles_list(request):
    """Liste des types de meubles"""
    types = TypeMeuble.objects.annotate(nombre_meubles=Count('meuble')).order_by('categorie', 'nom')
    
    context = {
        'types': types,
        'can_create': True,
    }
    return render(request, 'meubles/types/list.html', context)


@login_required
@gestionnaire_required
def type_meuble_create(request):
    """Créer un nouveau type de meuble"""
    if request.method == 'POST':
        form = TypeMeubleForm(request.POST)
        if form.is_valid():
            type_meuble = form.save()
            messages.success(request, f'Le type "{type_meuble.nom}" a été créé avec succès.')
            return redirect('meubles:types_list')
    else:
        form = TypeMeubleForm()
    
    context = {'form': form, 'action': 'Créer'}
    return render(request, 'meubles/types/form.html', context)


@login_required
@gestionnaire_required
def type_meuble_edit(request, pk):
    """Modifier un type de meuble"""
    type_meuble = get_object_or_404(TypeMeuble, pk=pk)
    
    if request.method == 'POST':
        form = TypeMeubleForm(request.POST, instance=type_meuble)
        if form.is_valid():
            form.save()
            messages.success(request, f'Le type "{type_meuble.nom}" a été modifié avec succès.')
            return redirect('meubles:types_list')
    else:
        form = TypeMeubleForm(instance=type_meuble)
    
    context = {'form': form, 'action': 'Modifier', 'objet': type_meuble}
    return render(request, 'meubles/types/form.html', context)


@login_required
@super_admin_required
def type_meuble_delete(request, pk):
    """Supprimer un type de meuble - SUPER ADMIN SEULEMENT"""
    type_meuble = get_object_or_404(TypeMeuble, pk=pk)
    
    if request.method == 'POST':
        nom = type_meuble.nom
        type_meuble.delete()
        messages.success(request, f'Le type "{nom}" a été supprimé avec succès.')
        return redirect('meubles:types_list')
    
    context = {'objet': type_meuble, 'type': 'type de meuble'}
    return render(request, 'meubles/confirm_delete.html', context)


# ======== GESTION DES MEUBLES ========

@login_required
@gestionnaire_required
def meubles_list(request):
    """Liste des meubles avec filtres"""
    form = MeubleFilterForm(request.GET)
    
    # Filtrer selon les permissions
    if hasattr(request.user, 'is_super_admin') and request.user.is_super_admin():
        meubles = Meuble.objects.all()
    else:
        meubles = Meuble.objects.filter(maison__gestionnaire=request.user)
    
    meubles = meubles.select_related('maison', 'type_meuble', 'ajoute_par')
    
    # Appliquer les filtres
    if form.is_valid():
        search = form.cleaned_data.get('search')
        maison = form.cleaned_data.get('maison')
        type_meuble = form.cleaned_data.get('type_meuble')
        etat = form.cleaned_data.get('etat')
        piece = form.cleaned_data.get('piece')
        verification_requise = form.cleaned_data.get('verification_requise')
        
        if search:
            meubles = meubles.filter(
                Q(nom__icontains=search) |
                Q(numero_serie__icontains=search) |
                Q(marque__icontains=search) |
                Q(modele__icontains=search)
            )
        
        if maison:
            meubles = meubles.filter(maison=maison)
        if type_meuble:
            meubles = meubles.filter(type_meuble=type_meuble)
        if etat:
            meubles = meubles.filter(etat=etat)
        if piece:
            meubles = meubles.filter(piece=piece)
        if verification_requise:
            # Meubles sans vérification ou vérification ancienne
            meubles = meubles.filter(
                Q(date_derniere_verification__isnull=True) |
                Q(date_derniere_verification__lt=timezone.now().date() - timedelta(days=180))
            )
    
    # Tri
    sort_by = request.GET.get('sort', '-date_creation')
    valid_sorts = [
        'nom', 'numero_serie', 'maison__nom', 'type_meuble__nom',
        'etat', 'date_entree', 'date_creation', '-date_creation'
    ]
    if sort_by in valid_sorts:
        meubles = meubles.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(meubles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'can_create': True,
    }
    return render(request, 'meubles/meubles/list.html', context)


@login_required
@gestionnaire_required
def meuble_create(request):
    """Créer un nouveau meuble"""
    if request.method == 'POST':
        form = MeubleForm(request.POST, user=request.user)
        if form.is_valid():
            meuble = form.save(commit=False)
            meuble.ajoute_par = request.user
            meuble.save()
            
            messages.success(request, f'Le meuble "{meuble.nom}" a été créé avec succès.')
            return redirect('meubles:meubles_list')
    else:
        form = MeubleForm(user=request.user)
    
    context = {'form': form, 'action': 'Créer'}
    return render(request, 'meubles/meubles/form.html', context)


@login_required
@gestionnaire_required
def meuble_detail(request, pk):
    """Détail d'un meuble"""
    meuble = get_object_or_404(Meuble, pk=pk)
    
    # Vérifier les permissions
    if not _can_manage_meuble(request.user, meuble):
        messages.error(request, "Vous n'avez pas les droits pour voir ce meuble.")
        return redirect('meubles:meubles_list')
    
    # Historique des états
    historique = meuble.historique_etats.all().order_by('-date_changement')[:10]
    
    # Photos
    photos = meuble.photos.all().order_by('-date_prise')
    
    context = {
        'meuble': meuble,
        'historique': historique,
        'photos': photos,
        'can_edit': _can_manage_meuble(request.user, meuble),
    }
    return render(request, 'meubles/meubles/detail.html', context)


@login_required
@gestionnaire_required
def meuble_edit(request, pk):
    """Modifier un meuble"""
    meuble = get_object_or_404(Meuble, pk=pk)
    
    if not _can_manage_meuble(request.user, meuble):
        messages.error(request, "Vous n'avez pas les droits pour modifier ce meuble.")
        return redirect('meubles:meubles_list')
    
    if request.method == 'POST':
        form = MeubleForm(request.POST, instance=meuble, user=request.user)
        if form.is_valid():
            ancien_etat = meuble.etat
            nouveau_meuble = form.save()
            
            # Créer un historique si l'état a changé
            if ancien_etat != nouveau_meuble.etat:
                HistoriqueEtatMeuble.objects.create(
                    meuble=nouveau_meuble,
                    ancien_etat=ancien_etat,
                    nouvel_etat=nouveau_meuble.etat,
                    modifie_par=request.user,
                    motif="Modification via formulaire"
                )
            
            messages.success(request, f'Le meuble "{meuble.nom}" a été modifié avec succès.')
            return redirect('meubles:meuble_detail', pk=meuble.pk)
    else:
        form = MeubleForm(instance=meuble, user=request.user)
    
    context = {'form': form, 'action': 'Modifier', 'objet': meuble}
    return render(request, 'meubles/meubles/form.html', context)


@login_required
@gestionnaire_required
def meuble_delete(request, pk):
    """Supprimer un meuble"""
    meuble = get_object_or_404(Meuble, pk=pk)
    
    if not _can_manage_meuble(request.user, meuble):
        messages.error(request, "Vous n'avez pas les droits pour supprimer ce meuble.")
        return redirect('meubles:meubles_list')
    
    if request.method == 'POST':
        nom = meuble.nom
        meuble.delete()
        messages.success(request, f'Le meuble "{nom}" a été supprimé avec succès.')
        return redirect('meubles:meubles_list')
    
    context = {'objet': meuble, 'type': 'meuble'}
    return render(request, 'meubles/confirm_delete.html', context)


# ======== ACTIONS RAPIDES SUR LES MEUBLES ========

@login_required
@gestionnaire_required
@require_http_methods(["POST"])
def meuble_changer_etat(request, pk):
    """Changer l'état d'un meuble via AJAX"""
    meuble = get_object_or_404(Meuble, pk=pk)
    
    if not _can_manage_meuble(request.user, meuble):
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    nouvel_etat = request.POST.get('etat')
    motif = request.POST.get('motif', '')
    
    if nouvel_etat not in dict(Meuble.ETAT_CHOICES):
        return JsonResponse({'success': False, 'error': 'État invalide'})
    
    ancien_etat = meuble.etat
    meuble.etat = nouvel_etat
    
    if nouvel_etat in ['bon', 'usage']:
        meuble.date_derniere_verification = timezone.now().date()
    
    meuble.save()
    
    # Créer l'historique
    HistoriqueEtatMeuble.objects.create(
        meuble=meuble,
        ancien_etat=ancien_etat,
        nouvel_etat=nouvel_etat,
        modifie_par=request.user,
        motif=motif or f"Changement d'état via interface"
    )
    
    return JsonResponse({
        'success': True,
        'message': f'État changé de "{ancien_etat}" à "{nouvel_etat}"'
    })


@login_required
@gestionnaire_required
@require_http_methods(["POST"])
def meuble_marquer_verifie(request, pk):
    """Marquer un meuble comme vérifié"""
    meuble = get_object_or_404(Meuble, pk=pk)
    
    if not _can_manage_meuble(request.user, meuble):
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    meuble.date_derniere_verification = timezone.now().date()
    meuble.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Meuble marqué comme vérifié'
    })


# ======== INVENTAIRES ========

@login_required
@gestionnaire_required
def inventaires_list(request):
    """Liste des inventaires"""
    # Filtrer selon les permissions
    if hasattr(request.user, 'is_super_admin') and request.user.is_super_admin():
        inventaires = InventaireMaison.objects.all()
    else:
        inventaires = InventaireMaison.objects.filter(maison__gestionnaire=request.user)
    
    inventaires = inventaires.select_related('maison', 'effectue_par').order_by('-date_inventaire')
    
    # Pagination
    paginator = Paginator(inventaires, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'can_create': True,
    }
    return render(request, 'meubles/inventaires/list.html', context)


@login_required
@gestionnaire_required
def inventaire_create(request):
    """Créer un nouvel inventaire"""
    if request.method == 'POST':
        form = InventaireForm(request.POST, user=request.user)
        if form.is_valid():
            inventaire = form.save(commit=False)
            inventaire.effectue_par = request.user
            inventaire.save()
            
            # Calculer automatiquement les statistiques
            inventaire.calculer_statistiques()
            
            messages.success(request, f'Inventaire créé pour {inventaire.maison.nom}.')
            return redirect('meubles:inventaire_detail', pk=inventaire.pk)
    else:
        form = InventaireForm(user=request.user)
    
    context = {'form': form, 'action': 'Créer'}
    return render(request, 'meubles/inventaires/form.html', context)


@login_required
@gestionnaire_required
def inventaire_detail(request, pk):
    """Détail d'un inventaire"""
    inventaire = get_object_or_404(InventaireMaison, pk=pk)
    
    # Vérifier les permissions
    if not _can_manage_maison(request.user, inventaire.maison):
        messages.error(request, "Vous n'avez pas les droits pour voir cet inventaire.")
        return redirect('meubles:inventaires_list')
    
    # Meubles de la maison au moment de l'inventaire
    meubles = inventaire.maison.meubles.all().select_related('type_meuble')
    
    # Répartition par état
    repartition_etats = meubles.values('etat').annotate(count=Count('id'))
    
    # Répartition par pièce
    repartition_pieces = meubles.values('piece').annotate(count=Count('id'))
    
    context = {
        'inventaire': inventaire,
        'meubles': meubles,
        'repartition_etats': repartition_etats,
        'repartition_pieces': repartition_pieces,
    }
    return render(request, 'meubles/inventaires/detail.html', context)


# ======== PHOTOS DE MEUBLES ========

@login_required
@gestionnaire_required
def meuble_add_photo(request, meuble_pk):
    """Ajouter une photo à un meuble"""
    meuble = get_object_or_404(Meuble, pk=meuble_pk)
    
    if not _can_manage_meuble(request.user, meuble):
        messages.error(request, "Vous n'avez pas les droits pour ajouter des photos à ce meuble.")
        return redirect('meubles:meuble_detail', pk=meuble.pk)
    
    if request.method == 'POST':
        form = PhotoMeubleForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.meuble = meuble
            photo.save()
            
            messages.success(request, 'Photo ajoutée avec succès.')
            return redirect('meubles:meuble_detail', pk=meuble.pk)
    else:
        form = PhotoMeubleForm()
    
    context = {
        'form': form,
        'meuble': meuble,
        'action': 'Ajouter une photo'
    }
    return render(request, 'meubles/photos/form.html', context)


# ======== FONCTIONS UTILITAIRES ========

def _can_manage_meuble(user, meuble):
    """Vérifie si un utilisateur peut gérer un meuble"""
    if user.is_anonymous:
        return False
    if hasattr(user, 'is_super_admin') and user.is_super_admin():
        return True
    if user.is_superuser:
        return True
    return meuble.maison.gestionnaire == user


def _can_manage_maison(user, maison):
    """Vérifie si un utilisateur peut gérer une maison"""
    if user.is_anonymous:
        return False
    if hasattr(user, 'is_super_admin') and user.is_super_admin():
        return True
    if user.is_superuser:
        return True
    return maison.gestionnaire == user


# ======== VUES POUR L'INTÉGRATION AVEC HOME ========

@login_required
@gestionnaire_required
def maison_meubles_list(request, maison_id):
    """Liste des meubles d'une maison spécifique"""
    maison = get_object_or_404(Maison, id=maison_id)
    
    if not _can_manage_maison(request.user, maison):
        messages.error(request, "Vous n'avez pas les droits pour voir les meubles de cette maison.")
        return redirect('home:maisons_list')
    
    meubles = maison.meubles.all().select_related('type_meuble')
    
    # Statistiques de la maison
    stats = {
        'total': meubles.count(),
        'bon_etat': meubles.filter(etat='bon').count(),
        'defectueux': meubles.filter(etat='defectueux').count(),
        'usage': meubles.filter(etat='usage').count(),
        'hors_service': meubles.filter(etat='hors_service').count(),
    }
    
    # Répartition par pièce
    meubles_par_piece = {}
    for meuble in meubles:
        piece = meuble.get_piece_display()
        if piece not in meubles_par_piece:
            meubles_par_piece[piece] = []
        meubles_par_piece[piece].append(meuble)
    
    context = {
        'maison': maison,
        'meubles': meubles,
        'stats': stats,
        'meubles_par_piece': meubles_par_piece,
    }
    return render(request, 'meubles/maison_meubles.html', context)


# ======== API POUR AJAX ========

@login_required
@gestionnaire_required
def api_meubles_maison(request, maison_id):
    """API pour récupérer les meubles d'une maison"""
    maison = get_object_or_404(Maison, id=maison_id)
    
    if not _can_manage_maison(request.user, maison):
        return JsonResponse({'error': 'Permissions insuffisantes'}, status=403)
    
    meubles = maison.meubles.all().select_related('type_meuble')
    
    data = []
    for meuble in meubles:
        data.append({
            'id': meuble.id,
            'nom': meuble.nom,
            'type': meuble.type_meuble.nom,
            'etat': meuble.etat,
            'etat_display': meuble.get_etat_display(),
            'piece': meuble.get_piece_display(),
            'numero_serie': meuble.numero_serie,
        })
    
    return JsonResponse({'meubles': data})