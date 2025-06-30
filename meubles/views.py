from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum, Case, When, IntegerField
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from datetime import datetime, timedelta
import csv
import io

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
from .forms import (MeubleForm, TypeMeubleForm, MeubleFilterForm, InventaireForm, 
                   PhotoMeubleForm, MeubleImportForm, RapportMeublesForm)
from home.models import Maison


def get_optimized_stats(user):
    """Calcule les statistiques optimisées pour le dashboard"""
    # Requête de base sécurisée
    meubles_qs = Meuble.objects.select_related('maison', 'type_meuble')
    
    if hasattr(user, 'is_super_admin') and user.is_super_admin():
        meubles = meubles_qs.all()
        maisons = Maison.objects.all()
    else:
        meubles = meubles_qs.filter(maison__gestionnaire=user)
        maisons = Maison.objects.filter(gestionnaire=user)
    
    # Statistiques en une seule requête
    stats_agg = meubles.aggregate(
        total=Count('id'),
        bon_etat=Count(Case(When(etat='bon', then=1), output_field=IntegerField())),
        defectueux=Count(Case(When(etat='defectueux', then=1), output_field=IntegerField())),
        usage=Count(Case(When(etat='usage', then=1), output_field=IntegerField())),
        hors_service=Count(Case(When(etat='hors_service', then=1), output_field=IntegerField())),
    )
    
    # Valeurs par défaut pour éviter les erreurs
    for key in ['total', 'bon_etat', 'defectueux', 'usage', 'hors_service']:
        if stats_agg[key] is None:
            stats_agg[key] = 0
    
    # Meubles nécessitant vérification (vérification des champs avant utilisation)
    cutoff_date = timezone.now().date() - timedelta(days=180)
    
    # Vérifier si le champ date_derniere_verification existe
    try:
        verification_count = meubles.filter(
            Q(date_derniere_verification__isnull=True) |
            Q(date_derniere_verification__lt=cutoff_date)
        ).count()
    except Exception:
        # Si le champ n'existe pas, on met 0
        verification_count = 0
    
    stats_agg.update({
        'meubles_a_verifier': verification_count,
        'total_maisons': maisons.count(),
        'total_types': TypeMeuble.objects.count(),
    })
    
    # Calcul des pourcentages
    total = stats_agg['total'] or 1  # Éviter division par zéro
    stats_agg.update({
        'pourcentage_bon_etat': round((stats_agg['bon_etat'] / total) * 100, 1),
        'pourcentage_defectueux': round((stats_agg['defectueux'] / total) * 100, 1),
    })
    
    return stats_agg


# ======== MIXINS ET UTILITAIRES ========

class PermissionMixin:
    """Mixin pour gérer les permissions"""
    
    def get_user_queryset(self, model_class, relation_field=None):
        """Retourne le queryset filtré selon les permissions utilisateur"""
        if hasattr(self.request.user, 'is_super_admin') and self.request.user.is_super_admin():
            return model_class.objects.all()
        
        if relation_field:
            filter_dict = {f"{relation_field}__gestionnaire": self.request.user}
            return model_class.objects.filter(**filter_dict)
        
        # Pour les maisons directement
        if model_class == Maison:
            return model_class.objects.filter(gestionnaire=self.request.user)
        
        return model_class.objects.none()
    
    def can_manage_object(self, obj):
        """Vérifie si l'utilisateur peut gérer cet objet"""
        if hasattr(self.request.user, 'is_super_admin') and self.request.user.is_super_admin():
            return True
        
        if hasattr(obj, 'maison'):
            return obj.maison.gestionnaire == self.request.user
        elif hasattr(obj, 'gestionnaire'):
            return obj.gestionnaire == self.request.user
        
        return False


def get_optimized_stats(user):
    """Calcule les statistiques optimisées pour le dashboard"""
    meubles_qs = Meuble.objects.select_related('maison', 'type_meuble')
    
    if hasattr(user, 'is_super_admin') and user.is_super_admin():
        meubles = meubles_qs.all()
        maisons = Maison.objects.all()
    else:
        meubles = meubles_qs.filter(maison__gestionnaire=user)
        maisons = Maison.objects.filter(gestionnaire=user)
    
    # Statistiques en une seule requête
    stats_agg = meubles.aggregate(
        total=Count('id'),
        bon_etat=Count(Case(When(etat='bon', then=1), output_field=IntegerField())),
        defectueux=Count(Case(When(etat='defectueux', then=1), output_field=IntegerField())),
        usage=Count(Case(When(etat='usage', then=1), output_field=IntegerField())),
        hors_service=Count(Case(When(etat='hors_service', then=1), output_field=IntegerField())),
        valeur_totale=Sum('valeur_actuelle'),
        prix_total=Sum('prix_achat'),
    )
    
    # Meubles nécessitant vérification
    cutoff_date = timezone.now().date() - timedelta(days=180)
    verification_count = meubles.filter(
        Q(date_derniere_verification__isnull=True) |
        Q(date_derniere_verification__lt=cutoff_date)
    ).count()
    
    stats_agg.update({
        'meubles_a_verifier': verification_count,
        'total_maisons': maisons.count(),
        'total_types': TypeMeuble.objects.count(),
    })
    
    # Calcul des pourcentages
    total = stats_agg['total'] or 1  # Éviter division par zéro
    stats_agg.update({
        'pourcentage_bon_etat': round((stats_agg['bon_etat'] / total) * 100, 1),
        'pourcentage_defectueux': round((stats_agg['defectueux'] / total) * 100, 1),
    })
    
    return stats_agg


# ======== DASHBOARD ========

@login_required
@gestionnaire_required
def meubles_dashboard(request):
    """Dashboard optimisé et sécurisé"""
    try:
        stats = get_optimized_stats(request.user)
        
        # Queryset de base avec gestion d'erreurs
        if hasattr(request.user, 'is_super_admin') and request.user.is_super_admin():
            meubles_base = Meuble.objects.select_related('maison', 'type_meuble')
            maisons_base = Maison.objects.all()
        else:
            meubles_base = Meuble.objects.filter(maison__gestionnaire=request.user).select_related('maison', 'type_meuble')
            maisons_base = Maison.objects.filter(gestionnaire=request.user)
        
        # Répartitions optimisées avec gestion d'erreurs
        try:
            # Utiliser seulement les champs qui existent certainement
            repartition_types = meubles_base.values('type_meuble__nom').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
        except Exception as e:
            print(f"Erreur repartition_types: {e}")
            repartition_types = []
        
        try:
            # Utiliser seulement le champ etat du modèle Meuble
            repartition_etats = meubles_base.values('etat').annotate(
                count=Count('id')
            ).order_by('-count')
        except Exception as e:
            print(f"Erreur repartition_etats: {e}")
            repartition_etats = []
        
        # Données récentes avec gestion d'erreurs
        try:
            # Récupérer seulement les champs de base qui existent
            meubles_recents = meubles_base.order_by('-id')[:5]  # Utiliser l'ID au lieu de date_creation si problème
        except Exception as e:
            print(f"Erreur meubles_recents: {e}")
            meubles_recents = []
        
        # Meubles nécessitant attention avec gestion d'erreurs
        try:
            # Construire la requête avec seulement les champs qui existent
            attention_filter = Q(etat='defectueux')
            
            meubles_attention = meubles_base.filter(attention_filter)[:5]
            
        except Exception as e:
            print(f"Erreur meubles_attention: {e}")
            meubles_attention = []
        
        # Maisons avec problèmes
        try:
            maisons_problemes = maisons_base.annotate(
                meubles_defectueux=Count('meubles', filter=Q(meubles__etat='defectueux'))
            ).filter(meubles_defectueux__gt=0).order_by('-meubles_defectueux')[:5]
        except Exception as e:
            print(f"Erreur maisons_problemes: {e}")
            maisons_problemes = []
        
        context = {
            'stats': stats,
            'repartition_types': repartition_types,
            'repartition_etats': repartition_etats,
            'meubles_recents': meubles_recents,
            'meubles_attention': meubles_attention,
            'maisons_problemes': maisons_problemes,
            'is_super_admin': hasattr(request.user, 'is_super_admin') and request.user.is_super_admin(),
        }
        
        return render(request, 'meubles/dashboard.html', context)
        
    except Exception as e:
        # En cas d'erreur générale, afficher un dashboard minimal
        messages.error(request, f"Erreur lors du chargement du dashboard: {str(e)}")
        
        context = {
            'stats': {
                'total': 0,
                'bon_etat': 0,
                'defectueux': 0,
                'usage': 0,
                'hors_service': 0,
                'meubles_a_verifier': 0,
                'pourcentage_bon_etat': 0,
                'pourcentage_defectueux': 0,
            },
            'repartition_types': [],
            'repartition_etats': [],
            'meubles_recents': [],
            'meubles_attention': [],
            'maisons_problemes': [],
            'is_super_admin': False,
        }
        
        return render(request, 'meubles/dashboard.html', context)    
# ======== TYPES DE MEUBLES ========

@login_required
@gestionnaire_required
def types_meubles_list(request):
    """Liste optimisée des types de meubles"""
    types = TypeMeuble.objects.annotate(
        nb_meubles=Count('meuble')  # Changé de nombre_meubles à nb_meubles
    ).order_by('categorie', 'nom')
    
    # Calculer les statistiques
    types_utilises_count = types.filter(nb_meubles__gt=0).count()
    total_meubles = sum(type_obj.nb_meubles for type_obj in types)
    
    # Compter les catégories uniques
    categories_count = types.values('categorie').distinct().count()
    
    context = {
        'types': types,
        'types_utilises_count': types_utilises_count,
        'total_meubles': total_meubles,
        'categories_count': categories_count,
    }
    
    return render(request, 'meubles/types/list.html', context)

@login_required
@gestionnaire_required
def type_meuble_create(request):
    """Créer un type de meuble"""
    if request.method == 'POST':
        form = TypeMeubleForm(request.POST)
        if form.is_valid():
            type_meuble = form.save()
            messages.success(request, f'Type "{type_meuble.nom}" créé avec succès.')
            return redirect('meubles:types_list')
    else:
        form = TypeMeubleForm()
    
    return render(request, 'meubles/types/form.html', {'form': form, 'action': 'Créer'})


@login_required
@gestionnaire_required
def type_meuble_edit(request, pk):
    """Modifier un type de meuble"""
    type_meuble = get_object_or_404(TypeMeuble, pk=pk)
    
    if request.method == 'POST':
        form = TypeMeubleForm(request.POST, instance=type_meuble)
        if form.is_valid():
            form.save()
            messages.success(request, f'Type "{type_meuble.nom}" modifié avec succès.')
            return redirect('meubles:types_list')
    else:
        form = TypeMeubleForm(instance=type_meuble)
    
    return render(request, 'meubles/types/form.html', {
        'form': form, 'action': 'Modifier', 'objet': type_meuble
    })


@login_required
@super_admin_required
def type_meuble_delete(request, pk):
    """Supprimer un type de meuble"""
    type_meuble = get_object_or_404(TypeMeuble, pk=pk)
    
    if request.method == 'POST':
        nom = type_meuble.nom
        type_meuble.delete()
        messages.success(request, f'Type "{nom}" supprimé avec succès.')
        return redirect('meubles:types_list')
    
    return render(request, 'meubles/confirm_delete.html', {
        'objet': type_meuble, 'type': 'type de meuble'
    })


# ======== MEUBLES ========

@login_required
@gestionnaire_required
def meubles_list(request):
    """Liste optimisée des meubles avec filtres"""
    permission_mixin = PermissionMixin()
    permission_mixin.request = request
    
    # Queryset optimisé
    meubles = permission_mixin.get_user_queryset(Meuble, 'maison').select_related(
        'maison', 'type_meuble', 'ajoute_par'
    ).prefetch_related('photos')
    
    # Filtres
    form = MeubleFilterForm(request.GET, user=request.user)
    if form.is_valid():
        cleaned_data = form.cleaned_data
        
        # Recherche textuelle
        if cleaned_data.get('search'):
            search_query = Q(nom__icontains=cleaned_data['search']) | \
                          Q(numero_serie__icontains=cleaned_data['search']) | \
                          Q(marque__icontains=cleaned_data['search']) | \
                          Q(modele__icontains=cleaned_data['search'])
            meubles = meubles.filter(search_query)
        
        # Filtres simples
        filters = ['maison', 'type_meuble', 'etat', 'piece']
        for field in filters:
            if cleaned_data.get(field):
                meubles = meubles.filter(**{field: cleaned_data[field]})
        
        # Vérification requise
        if cleaned_data.get('verification_requise'):
            cutoff_date = timezone.now().date() - timedelta(days=180)
            meubles = meubles.filter(
                Q(date_derniere_verification__isnull=True) |
                Q(date_derniere_verification__lt=cutoff_date)
            )
    
    # Tri
    sort_mapping = {
        'nom': 'nom',
        'numero': 'numero_serie',
        'maison': 'maison__nom',
        'type': 'type_meuble__nom',
        'etat': 'etat',
        'date_entree': 'date_entree',
        'recent': '-date_creation'
    }
    sort_by = sort_mapping.get(request.GET.get('sort', 'recent'), '-date_creation')
    meubles = meubles.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(meubles, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'meubles/list.html', {
        'page_obj': page_obj,
        'form': form,
    })


@login_required
@gestionnaire_required
def meuble_create(request):
    """Créer un meuble"""
    if request.method == 'POST':
        form = MeubleForm(request.POST, user=request.user)
        if form.is_valid():
            meuble = form.save(commit=False)
            meuble.ajoute_par = request.user
            meuble.save()
            messages.success(request, f'Meuble "{meuble.nom}" créé avec succès.')
            return redirect('meubles:meubles_list')
    else:
        form = MeubleForm(user=request.user)

    return render(request, 'meubles/form.html', {'form': form, 'action': 'Créer'})


@login_required
@gestionnaire_required
def meuble_detail(request, pk):
    """Détail optimisé d'un meuble"""
    meuble = get_object_or_404(
        Meuble.objects.select_related('maison', 'type_meuble', 'ajoute_par'),
        pk=pk
    )
    
    permission_mixin = PermissionMixin()
    permission_mixin.request = request
    
    if not permission_mixin.can_manage_object(meuble):
        messages.error(request, "Vous n'avez pas les droits pour voir ce meuble.")
        return redirect('meubles:meubles_list')
    
    # Historique et photos en une seule requête
    historique = meuble.historique_etats.select_related('modifie_par').order_by('-date_changement')[:10]
    photos = meuble.photos.order_by('-date_prise')
    
    context = {
        'meuble': meuble,
        'historique': historique,
        'photos': photos,
        'can_edit': True,
    }
    
    return render(request, 'meubles/detail.html', context)


@login_required
@gestionnaire_required
def meuble_edit(request, pk):
    """Modifier un meuble"""
    meuble = get_object_or_404(Meuble, pk=pk)
    
    permission_mixin = PermissionMixin()
    permission_mixin.request = request
    
    if not permission_mixin.can_manage_object(meuble):
        messages.error(request, "Vous n'avez pas les droits pour modifier ce meuble.")
        return redirect('meubles:meubles_list')
    
    if request.method == 'POST':
        form = MeubleForm(request.POST, instance=meuble, user=request.user)
        if form.is_valid():
            ancien_etat = meuble.etat
            nouveau_meuble = form.save()
            
            # Historique automatique
            if ancien_etat != nouveau_meuble.etat:
                HistoriqueEtatMeuble.objects.create(
                    meuble=nouveau_meuble,
                    ancien_etat=ancien_etat,
                    nouvel_etat=nouveau_meuble.etat,
                    modifie_par=request.user,
                    motif="Modification via formulaire"
                )
            
            messages.success(request, f'Meuble "{meuble.nom}" modifié avec succès.')
            return redirect('meubles:meuble_detail', pk=meuble.pk)
    else:
        form = MeubleForm(instance=meuble, user=request.user)
    
    return render(request, 'meubles/form.html', {
        'form': form, 'action': 'Modifier', 'objet': meuble
    })


@login_required
@gestionnaire_required
def meuble_delete(request, pk):
    """Supprimer un meuble"""
    meuble = get_object_or_404(Meuble, pk=pk)
    
    permission_mixin = PermissionMixin()
    permission_mixin.request = request
    
    if not permission_mixin.can_manage_object(meuble):
        messages.error(request, "Vous n'avez pas les droits pour supprimer ce meuble.")
        return redirect('meubles:meubles_list')
    
    if request.method == 'POST':
        nom = meuble.nom
        meuble.delete()
        messages.success(request, f'Meuble "{nom}" supprimé avec succès.')
        return redirect('meubles:meubles_list')
    
    return render(request, 'meubles/confirm_delete.html', {
        'objet': meuble, 'type': 'meuble'
    })


# ======== ACTIONS RAPIDES ========

@login_required
@gestionnaire_required
@require_http_methods(["POST"])
def meuble_changer_etat(request, pk):
    """Changer l'état d'un meuble via AJAX"""
    meuble = get_object_or_404(Meuble, pk=pk)
    
    permission_mixin = PermissionMixin()
    permission_mixin.request = request
    
    if not permission_mixin.can_manage_object(meuble):
        return JsonResponse({'success': False, 'error': 'Permissions insuffisantes'})
    
    nouvel_etat = request.POST.get('etat')
    motif = request.POST.get('motif', '')
    
    if nouvel_etat not in dict(Meuble.ETAT_CHOICES):
        return JsonResponse({'success': False, 'error': 'État invalide'})
    
    with transaction.atomic():
        ancien_etat = meuble.etat
        meuble.etat = nouvel_etat
        
        if nouvel_etat in ['bon', 'usage']:
            meuble.date_derniere_verification = timezone.now().date()
        
        meuble.save()
        
        # Historique
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
    
    permission_mixin = PermissionMixin()
    permission_mixin.request = request
    
    if not permission_mixin.can_manage_object(meuble):
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
    permission_mixin = PermissionMixin()
    permission_mixin.request = request
    
    inventaires = permission_mixin.get_user_queryset(
        InventaireMaison, 'maison'
    ).select_related('maison', 'effectue_par').order_by('-date_inventaire')

    # Ajout du compteur
    count_periodique = inventaires.filter(type_inventaire='periodique').count()
    count_entree = inventaires.filter(type_inventaire='entree').count()
    count_sortie = inventaires.filter(type_inventaire='sortie').count()
    
    paginator = Paginator(inventaires, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'meubles/inventaires/list.html', {
        'page_obj': page_obj,
        'count_periodique': count_periodique,
        'count_entree': count_entree,
        'count_sortie': count_sortie,
    })


@login_required
@gestionnaire_required
def inventaire_create(request):
    """Créer un inventaire"""
    if request.method == 'POST':
        form = InventaireForm(request.POST, user=request.user)
        if form.is_valid():
            inventaire = form.save(commit=False)
            inventaire.effectue_par = request.user
            inventaire.save()
            inventaire.calculer_statistiques()
            
            messages.success(request, f'Inventaire créé pour {inventaire.maison.nom}.')
            return redirect('meubles:inventaire_detail', pk=inventaire.pk)
    else:
        form = InventaireForm(user=request.user)
    
    return render(request, 'meubles/inventaires/form.html', {'form': form, 'action': 'Créer'})


@login_required
@gestionnaire_required
def inventaire_detail(request, pk):
    """Détail d'un inventaire"""
    inventaire = get_object_or_404(
        InventaireMaison.objects.select_related('maison', 'effectue_par'),
        pk=pk
    )
    
    permission_mixin = PermissionMixin()
    permission_mixin.request = request
    
    if not permission_mixin.can_manage_object(inventaire):
        messages.error(request, "Vous n'avez pas les droits pour voir cet inventaire.")
        return redirect('meubles:inventaires_list')
    
    # Meubles avec statistiques optimisées
    meubles = inventaire.maison.meubles.select_related('type_meuble')
    
    repartition_etats = meubles.values('etat').annotate(count=Count('id'))
    repartition_pieces = meubles.values('piece').annotate(count=Count('id'))
    
    context = {
        'inventaire': inventaire,
        'meubles': meubles,
        'repartition_etats': repartition_etats,
        'repartition_pieces': repartition_pieces,
    }
    
    return render(request, 'meubles/inventaires/detail.html', context)


# ======== PHOTOS ========

@login_required
@gestionnaire_required
def meuble_add_photo(request, meuble_pk):
    """Ajouter une photo à un meuble"""
    meuble = get_object_or_404(Meuble, pk=meuble_pk)
    
    permission_mixin = PermissionMixin()
    permission_mixin.request = request
    
    if not permission_mixin.can_manage_object(meuble):
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


# ======== IMPORT/EXPORT ========

@login_required
@gestionnaire_required
def meuble_import(request):
    """Import de meubles par CSV"""
    if request.method == 'POST':
        form = MeubleImportForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            fichier = form.cleaned_data['fichier_csv']
            maison = form.cleaned_data['maison']
            
            try:
                with transaction.atomic():
                    decoded_file = fichier.read().decode('utf-8')
                    csv_reader = csv.DictReader(io.StringIO(decoded_file))
                    
                    meubles_crees = []
                    erreurs = []
                    
                    for row_num, row in enumerate(csv_reader, start=2):
                        try:
                            # Créer le meuble
                            meuble = Meuble(
                                nom=row.get('nom', ''),
                                maison=maison,
                                piece=row.get('piece', 'salon'),
                                etat=row.get('etat', 'bon'),
                                marque=row.get('marque', ''),
                                modele=row.get('modele', ''),
                                ajoute_par=request.user
                            )
                            
                            # Type de meuble
                            type_nom = row.get('type_meuble', '')
                            if type_nom:
                                type_meuble, _ = TypeMeuble.objects.get_or_create(
                                    nom=type_nom,
                                    defaults={'categorie': 'autre'}
                                )
                                meuble.type_meuble = type_meuble
                            
                            # Générer numéro de série
                            count = maison.meubles.count() + len(meubles_crees) + 1
                            meuble.numero_serie = f"{maison.numero}-M{count:03d}"
                            
                            meuble.full_clean()
                            meuble.save()
                            meubles_crees.append(meuble)
                            
                        except Exception as e:
                            erreurs.append(f"Ligne {row_num}: {str(e)}")
                    
                    if erreurs:
                        messages.warning(request, f"{len(meubles_crees)} meubles importés avec {len(erreurs)} erreurs.")
                    else:
                        messages.success(request, f"{len(meubles_crees)} meubles importés avec succès.")
                    
                    return redirect('meubles:meubles_list')
                    
            except Exception as e:
                messages.error(request, f"Erreur lors de l'import: {str(e)}")
    else:
        form = MeubleImportForm(user=request.user)
    
    return render(request, 'meubles/import/form.html', {'form': form})


@login_required
@gestionnaire_required
def generer_rapport(request):
    """Générer des rapports"""
    if request.method == 'POST':
        form = RapportMeublesForm(request.POST, user=request.user)
        if form.is_valid():
            # Logique de génération de rapport
            type_rapport = form.cleaned_data['type_rapport']
            format_export = form.cleaned_data['format_export']
            
            # Ici vous implémenteriez la génération selon le type
            messages.success(request, f"Rapport {type_rapport} généré en {format_export}")
            return redirect('meubles:dashboard')
    else:
        form = RapportMeublesForm(user=request.user)
    
    return render(request, 'meubles/rapports/form.html', {'form': form})


# ======== INTÉGRATION MAISONS ========

@login_required
@gestionnaire_required
def maison_meubles_list(request, maison_id):
    """Meubles d'une maison spécifique"""
    maison = get_object_or_404(Maison, id=maison_id)
    
    permission_mixin = PermissionMixin()
    permission_mixin.request = request
    
    if not permission_mixin.can_manage_object(maison):
        messages.error(request, "Vous n'avez pas les droits pour voir les meubles de cette maison.")
        return redirect('home:maisons_list')
    
    meubles = maison.meubles.select_related('type_meuble').order_by('piece', 'nom')
    
    # Statistiques optimisées
    stats = meubles.aggregate(
        total=Count('id'),
        bon_etat=Count(Case(When(etat='bon', then=1), output_field=IntegerField())),
        defectueux=Count(Case(When(etat='defectueux', then=1), output_field=IntegerField())),
        usage=Count(Case(When(etat='usage', then=1), output_field=IntegerField())),
        hors_service=Count(Case(When(etat='hors_service', then=1), output_field=IntegerField())),
    )
    
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


# ======== API AJAX ========

@login_required
@gestionnaire_required
def api_meubles_maison(request, maison_id):
    """API pour récupérer les meubles d'une maison"""
    maison = get_object_or_404(Maison, id=maison_id)
    
    permission_mixin = PermissionMixin()
    permission_mixin.request = request
    
    if not permission_mixin.can_manage_object(maison):
        return JsonResponse({'error': 'Permissions insuffisantes'}, status=403)
    
    meubles = maison.meubles.select_related('type_meuble')
    
    data = [{
        'id': m.id,
        'nom': m.nom,
        'type': m.type_meuble.nom,
        'etat': m.etat,
        'etat_display': m.get_etat_display(),
        'piece': m.get_piece_display(),
        'numero_serie': m.numero_serie,
    } for m in meubles]
    
    return JsonResponse({'meubles': data})


@login_required
@gestionnaire_required
def api_meuble_stats(request, pk):
    """API pour les statistiques d'un meuble"""
    meuble = get_object_or_404(Meuble, pk=pk)
    
    permission_mixin = PermissionMixin()
    permission_mixin.request = request
    
    if not permission_mixin.can_manage_object(meuble):
        return JsonResponse({'error': 'Permissions insuffisantes'}, status=403)
    
    stats = {
        'age_mois': meuble.age_en_mois,
        'necessite_verification': meuble.necessite_verification,
        'depreciation': float(meuble.depreciation_estimee) if meuble.depreciation_estimee else 0,
        'historique_count': meuble.historique_etats.count(),
        'photos_count': meuble.photos.count(),
    }
    
    return JsonResponse(stats)