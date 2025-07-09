import json
import csv
import io
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum, Case, When, IntegerField
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from django.views.decorators.http import require_http_methods

# Imports ReportLab complets
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    PageBreak, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Import XlsxWriter
import xlsxwriter

# Imports pour vos modèles et formulaires
from .models import TypeMeuble, Meuble, HistoriqueEtatMeuble, PhotoMeuble, InventaireMaison
from .forms import RapportMeublesForm
from home.models import Maison

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



def get_user_display_name(user):
    """Fonction utilitaire pour récupérer le nom d'affichage de l'utilisateur"""
    if not user:
        return 'Système'
    
    # Essayer différentes façons d'obtenir le nom complet
    if hasattr(user, 'get_full_name') and callable(user.get_full_name):
        full_name = user.get_full_name()
        if full_name and full_name.strip():
            return full_name
    
    # Essayer avec first_name et last_name
    if hasattr(user, 'first_name') and hasattr(user, 'last_name'):
        first_name = getattr(user, 'first_name', '') or ''
        last_name = getattr(user, 'last_name', '') or ''
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            return full_name
    
    # Fallback sur username
    if hasattr(user, 'username'):
        return user.username
    
    return 'Utilisateur inconnu'

def generer_pdf_rapport(context, titre_rapport):
    """Générer un rapport PDF complet et professionnel"""
    try:
        # Créer la réponse HTTP
        response = HttpResponse(content_type='application/pdf')
        filename = f"rapport_{titre_rapport.lower().replace(' ', '_')}_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Créer le document PDF avec marges personnalisées
        doc = SimpleDocTemplate(
            response, 
            pagesize=A4,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch
        )
        story = []
        styles = getSampleStyleSheet()
        
        # Styles personnalisés
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1f2937'),
            alignment=TA_CENTER,
            spaceAfter=30,
            spaceBefore=10
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#4f46e5'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#374151'),
            spaceBefore=25,
            spaceAfter=15,
            borderWidth=1,
            borderColor=colors.HexColor('#e5e7eb'),
            borderPadding=5,
            backColor=colors.HexColor('#f9fafb')
        )
        
        # En-tête avec logo (simulé)
        header_data = [
            ['RepAvi Lodges - Gestion des Meubles', context['date_generation'].strftime('%d/%m/%Y à %H:%M')]
        ]
        header_table = Table(header_data, colWidths=[4*inch, 2.5*inch])
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 12),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica'),
            ('FONTSIZE', (1, 0), (1, 0), 10),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        story.append(header_table)
        
        # Titre principal
        story.append(Paragraph(f"<b>{context['type_rapport']}</b>", title_style))
        
        # Sous-titre avec informations contextuelles
        if context.get('maison'):
            subtitle_text = f"Maison: {context['maison'].nom}"
            if hasattr(context['maison'], 'adresse') and context['maison'].adresse:
                subtitle_text += f" - {context['maison'].adresse}"
            story.append(Paragraph(subtitle_text, subtitle_style))
        
        # Informations détaillées sur le rapport
        info_data = []
        
        # Utilisateur avec gestion d'erreur
        user = context.get('user')
        if user:
            user_name = get_user_display_name(user)
            info_data.append(['Généré par:', user_name])
        
        if context.get('maison'):
            info_data.extend([
                ['Maison:', context['maison'].nom],
                ['Numéro maison:', getattr(context['maison'], 'numero', 'N/A')],
                ['Adresse:', getattr(context['maison'], 'adresse', '') or 'Non renseignée'],
            ])
        
        # Calculs statistiques avancés
        meubles = context['meubles']
        total_meubles = meubles.count()
        
        date_debut = context.get('date_debut', 'début')
        date_fin = context.get('date_fin', "aujourd'hui")

        info_data.extend([
            ['Nombre total de meubles:', str(total_meubles)],
            ['Période du rapport:', f"Du {date_debut} au {date_fin}"],
        ])
        
        # Calculs financiers si disponibles
        try:
            valeur_totale = meubles.aggregate(
                total_achat=Sum('prix_achat'),
                total_actuel=Sum('valeur_actuelle')
            )
            
            if valeur_totale.get('total_achat'):
                info_data.append(['Valeur d\'achat totale:', f"{valeur_totale['total_achat']:,.0f} FCFA"])
            if valeur_totale.get('total_actuel'):
                info_data.append(['Valeur actuelle totale:', f"{valeur_totale['total_actuel']:,.0f} FCFA"])
                
        except Exception as e:
            print(f"Erreur calculs financiers PDF: {e}")
            pass  # Champs financiers non disponibles
        
        info_table = Table(info_data, colWidths=[2.2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 25))
        
        # Statistiques détaillées par état
        if total_meubles > 0:
            story.append(Paragraph("Répartition par État", section_style))
            
            # Calculer les statistiques par état avec gestion d'erreur
            try:
                stats_par_etat = meubles.values('etat').annotate(count=Count('id')).order_by('-count')
            except Exception as e:
                print(f"Erreur stats par état: {e}")
                stats_par_etat = []
            
            # Préparer les données pour le graphique textuel
            etats_labels = {
                'bon': 'Bon état',
                'usage': 'Usagé',
                'defectueux': 'Défectueux',
                'hors_service': 'Hors service'
            }
            
            stats_data = [['État', 'Nombre', 'Pourcentage', 'Barre de progression']]
            
            for stat in stats_par_etat:
                try:
                    etat = stat.get('etat', 'inconnu')
                    count = stat.get('count', 0)
                    pourcentage = (count / total_meubles * 100) if total_meubles > 0 else 0
                    
                    # Barre de progression textuelle
                    barre_longueur = int(pourcentage / 5)  # 1 caractère = 5%
                    barre = '█' * barre_longueur + '░' * (20 - barre_longueur)
                    
                    stats_data.append([
                        etats_labels.get(etat, etat.title()),
                        str(count),
                        f"{pourcentage:.1f}%",
                        barre
                    ])
                except Exception as e:
                    print(f"Erreur traitement stat: {e}")
                    continue
            
            # Ligne de total
            stats_data.append(['TOTAL', str(total_meubles), '100%', '████████████████████'])
            
            stats_table = Table(stats_data, colWidths=[1.8*inch, 1*inch, 1*inch, 2.5*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9fafb')]),
                ('FONTNAME', (3, 1), (3, -2), 'Courier'),  # Police monospace pour les barres
            ]))
            story.append(stats_table)
            story.append(Spacer(1, 20))
            
            # Répartition par pièce avec gestion d'erreur
            try:
                pieces_stats = meubles.values('piece').annotate(count=Count('id')).order_by('-count')[:8]
                
                if pieces_stats:
                    story.append(Paragraph("Répartition par Pièce (Top 8)", section_style))
                    
                    pieces_data = [['Pièce', 'Nombre', 'Pourcentage']]
                    
                    for piece_stat in pieces_stats:
                        try:
                            piece_value = piece_stat.get('piece', 'inconnu')
                            # Gestion sécurisée de get_piece_display
                            if hasattr(meubles.model, 'PIECE_CHOICES'):
                                piece_display = dict(meubles.model.PIECE_CHOICES).get(piece_value, piece_value)
                            else:
                                piece_display = str(piece_value).title()
                            
                            count = piece_stat.get('count', 0)
                            pourcentage = (count / total_meubles * 100) if total_meubles > 0 else 0
                            
                            pieces_data.append([piece_display, str(count), f"{pourcentage:.1f}%"])
                        except Exception as e:
                            print(f"Erreur piece stat: {e}")
                            continue
                    
                    pieces_table = Table(pieces_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
                    pieces_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
                    ]))
                    story.append(pieces_table)
                    story.append(Spacer(1, 25))
            except Exception as e:
                print(f"Erreur répartition pièces: {e}")
        
        # Nouvelle page pour le tableau principal
        story.append(PageBreak())
        
        # Tableau principal des meubles
        if context['meubles'].exists():
            story.append(Paragraph("Détail des Meubles", section_style))
            
            # Limiter le nombre de meubles pour éviter les PDF trop volumineux
            meubles_limit = context['meubles'][:100]
            
            # En-têtes optimisés selon la présence de maison
            if context.get('maison'):
                headers = ['Meuble', 'Type', 'Pièce', 'État', 'Entrée', 'Vérification', 'Valeur']
                col_widths = [2.2*inch, 1.3*inch, 1*inch, 1*inch, 0.8*inch, 0.9*inch, 0.9*inch]
            else:
                headers = ['Meuble', 'Maison', 'Type', 'Pièce', 'État', 'Entrée', 'Vérif.']
                col_widths = [1.8*inch, 1.2*inch, 1*inch, 0.8*inch, 0.8*inch, 0.7*inch, 0.7*inch]
            
            # Données du tableau
            table_data = [headers]
            
            for meuble in meubles_limit:
                try:
                    # Préparer les données de base avec gestion sécurisée
                    nom_complet = str(getattr(meuble, 'nom', 'Sans nom'))
                    numero_serie = getattr(meuble, 'numero_serie', '')
                    if numero_serie:
                        nom_complet += f"\n({numero_serie})"
                    
                    type_meuble = ''
                    if hasattr(meuble, 'type_meuble') and meuble.type_meuble:
                        type_meuble = str(getattr(meuble.type_meuble, 'nom', 'N/D'))
                    else:
                        type_meuble = 'N/D'
                    
                    # Gestion sécurisée de get_piece_display
                    try:
                        if hasattr(meuble, 'get_piece_display'):
                            piece = meuble.get_piece_display()
                        else:
                            piece = str(getattr(meuble, 'piece', 'N/D'))
                    except:
                        piece = 'N/D'
                    
                    # Gestion sécurisée de get_etat_display
                    try:
                        if hasattr(meuble, 'get_etat_display'):
                            etat = meuble.get_etat_display()
                        else:
                            etat = str(getattr(meuble, 'etat', 'N/D'))
                    except:
                        etat = 'N/D'
                    
                    # Date d'entrée
                    date_entree = 'N/D'
                    if hasattr(meuble, 'date_entree') and meuble.date_entree:
                        try:
                            date_entree = meuble.date_entree.strftime('%d/%m/%Y')
                        except:
                            date_entree = 'N/D'
                    
                    # Vérification
                    verification = 'Jamais'
                    if hasattr(meuble, 'date_derniere_verification') and meuble.date_derniere_verification:
                        try:
                            verification = meuble.date_derniere_verification.strftime('%d/%m/%Y')
                        except:
                            verification = 'Erreur'
                    
                    if context.get('maison'):
                        # Valeur pour maison spécifique
                        valeur = 'N/E'
                        try:
                            if hasattr(meuble, 'valeur_actuelle') and meuble.valeur_actuelle:
                                valeur = f"{float(meuble.valeur_actuelle):,.0f}"
                            elif hasattr(meuble, 'prix_achat') and meuble.prix_achat:
                                valeur = f"{float(meuble.prix_achat):,.0f}"
                        except:
                            valeur = 'N/E'
                        
                        row = [nom_complet, type_meuble, piece, etat, date_entree, verification, valeur]
                    else:
                        # Vue multi-maisons
                        maison_nom = 'N/D'
                        if hasattr(meuble, 'maison') and meuble.maison:
                            maison_nom = str(getattr(meuble.maison, 'nom', 'N/D'))
                        
                        row = [nom_complet, maison_nom, type_meuble, piece, etat, date_entree, verification]
                    
                    table_data.append(row)
                    
                except Exception as e:
                    print(f"Erreur traitement meuble {getattr(meuble, 'id', 'inconnu')}: {e}")
                    continue
            
            # Créer et styliser le tableau
            main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            # Style du tableau avec couleurs selon l'état
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]
            
            # Appliquer des couleurs selon l'état avec gestion d'erreur
            for i, meuble in enumerate(meubles_limit, 1):
                try:
                    etat = getattr(meuble, 'etat', '')
                    if etat == 'defectueux':
                        table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fef2f2')))
                    elif etat == 'hors_service':
                        table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fafafa')))
                    elif etat == 'bon':
                        table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f0fdf4')))
                    else:  # usage
                        table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fffbeb')))
                except Exception as e:
                    print(f"Erreur style meuble {i}: {e}")
                    continue
            
            main_table.setStyle(TableStyle(table_style))
            story.append(main_table)
            
            # Note sur la limitation
            if context['meubles'].count() > 100:
                story.append(Spacer(1, 15))
                note_style = ParagraphStyle(
                    'Note',
                    parent=styles['Normal'],
                    fontSize=9,
                    textColor=colors.HexColor('#6b7280'),
                    alignment=TA_CENTER,
                    fontName='Helvetica-Oblique'
                )
                story.append(Paragraph(
                    f"<i>Note: Seuls les 100 premiers meubles sont affichés dans ce rapport PDF. "
                    f"Total des meubles: {context['meubles'].count()}. "
                    f"Utilisez l'export Excel pour obtenir la liste complète.</i>",
                    note_style
                ))
        
        # Pied de page avec résumé
        story.append(Spacer(1, 30))
        
        footer_data = [
            ['RepAvi Lodges - Système de Gestion des Meubles', ''],
            [f'Rapport généré le {context["date_generation"].strftime("%d/%m/%Y à %H:%M")}', ''],
        ]
        
        # Utilisateur avec gestion sécurisée
        user = context.get('user')
        if user:
            user_name = get_user_display_name(user)
            footer_data.append([f'Par {user_name}', ''])
        
        footer_data.append([f'Total: {total_meubles} meuble{"s" if total_meubles > 1 else ""}', 'Page 1/1'])
        
        footer_table = Table(footer_data, colWidths=[4*inch, 2.5*inch])
        footer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#6b7280')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#e5e7eb')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(footer_table)
        
        # Construire le PDF
        doc.build(story)
        return response
        
    except Exception as e:
        print(f"Erreur génération PDF: {e}")
        # En cas d'erreur, retourner un PDF d'erreur simple
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="erreur_rapport.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=A4)
        styles = getSampleStyleSheet()
        
        error_story = [
            Paragraph("Erreur de génération du rapport", styles['Title']),
            Paragraph(f"Une erreur s'est produite: {str(e)}", styles['Normal']),
            Paragraph("Veuillez contacter l'administrateur.", styles['Normal'])
        ]
        
        doc.build(error_story)
        return response


def export_meubles_csv(request):
    """Exporter les meubles en CSV avec encodage UTF-8"""
    try:
        # Permissions
        if hasattr(request.user, 'is_super_admin') and request.user.is_super_admin():
            meubles = Meuble.objects.select_related('maison', 'type_meuble', 'ajoute_par')
        else:
            meubles = Meuble.objects.filter(maison__gestionnaire=request.user).select_related('maison', 'type_meuble', 'ajoute_par')
        
        # Appliquer les filtres si fournis
        maison_id = request.GET.get('maison')
        if maison_id:
            meubles = meubles.filter(maison_id=maison_id)
        
        type_rapport = request.GET.get('type_rapport', 'inventaire')
        if type_rapport == 'defectueux':
            meubles = meubles.filter(etat='defectueux')
        elif type_rapport == 'verification':
            cutoff_date = timezone.now().date() - timedelta(days=180)
            meubles = meubles.filter(
                Q(date_derniere_verification__isnull=True) |
                Q(date_derniere_verification__lt=cutoff_date)
            )
        
        # Créer la réponse CSV
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        timestamp = timezone.now().strftime("%Y%m%d_%H%M")
        filename = f"meubles_{type_rapport}_{timestamp}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # BOM UTF-8 pour Excel
        response.write('\ufeff')
        
        writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_ALL)
        
        # En-têtes détaillés
        headers = [
            'ID', 'Nom', 'Numéro de série', 'Maison', 'Numéro maison', 'Type de meuble', 
            'Catégorie', 'Pièce', 'État', 'Marque', 'Modèle', 'Couleur',
            'Date d\'entrée', 'Prix d\'achat (FCFA)', 'Valeur actuelle (FCFA)', 
            'Dernière vérification', 'Observations', 'Ajouté par', 'Date de création'
        ]
        writer.writerow(headers)
        
        # Données
        for meuble in meubles:
            try:
                row = [
                    str(meuble.id),
                    meuble.nom or '',
                    getattr(meuble, 'numero_serie', '') or '',
                    meuble.maison.nom if meuble.maison else '',
                    getattr(meuble.maison, 'numero', '') if meuble.maison else '',
                    meuble.type_meuble.nom if meuble.type_meuble else '',
                    getattr(meuble.type_meuble, 'categorie', '') if meuble.type_meuble else '',
                    meuble.get_piece_display() if hasattr(meuble, 'get_piece_display') else '',
                    meuble.get_etat_display() if hasattr(meuble, 'get_etat_display') else meuble.etat,
                    getattr(meuble, 'marque', '') or '',
                    getattr(meuble, 'modele', '') or '',
                    getattr(meuble, 'couleur', '') or '',
                    meuble.date_entree.strftime('%d/%m/%Y') if meuble.date_entree else '',
                    str(meuble.prix_achat) if hasattr(meuble, 'prix_achat') and meuble.prix_achat else '',
                    str(meuble.valeur_actuelle) if hasattr(meuble, 'valeur_actuelle') and meuble.valeur_actuelle else '',
                    meuble.date_derniere_verification.strftime('%d/%m/%Y') if hasattr(meuble, 'date_derniere_verification') and meuble.date_derniere_verification else '',
                    getattr(meuble, 'observations', '') or '',
                    meuble.ajoute_par.get_full_name() if meuble.ajoute_par else '',
                    getattr(meuble, 'date_creation', timezone.now()).strftime('%d/%m/%Y') if hasattr(meuble, 'date_creation') else ''
                ]
                writer.writerow(row)
            except Exception as e:
                # En cas d'erreur sur un meuble spécifique, on continue
                print(f"Erreur export CSV meuble {meuble.id}: {e}")
                continue
        
        return response
        
    except Exception as e:
        messages.error(request, f"Erreur lors de l'export CSV: {str(e)}")
        return redirect('meubles:meubles_list')
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

def generer_excel_rapport(context, titre_rapport):
    """Générer un rapport Excel complet"""
    try:
        # Créer la réponse HTTP
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f"rapport_{titre_rapport.lower().replace(' ', '_')}_{timezone.now().strftime('%Y%m%d_%H%M')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Créer le classeur Excel en mémoire
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4f46e5',
            'font_color': 'white'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#e5e7eb',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'valign': 'top'
        })
        
        date_format = workbook.add_format({
            'border': 1,
            'num_format': 'dd/mm/yyyy'
        })
        
        money_format = workbook.add_format({
            'border': 1,
            'num_format': '#,##0 "FCFA"'
        })
        
        # Feuille principale - Meubles
        worksheet = workbook.add_worksheet('Meubles')
        
        # Titre
        worksheet.merge_range('A1:H1', f"{context['type_rapport']}", title_format)
        worksheet.set_row(0, 25)
        
        # Informations générales
        row = 2
        worksheet.write(row, 0, 'Date de génération:', header_format)
        worksheet.write(row, 1, context['date_generation'].strftime('%d/%m/%Y %H:%M'), cell_format)
        row += 1
        
        if context.get('user'):
            user_name = getattr(context['user'], 'get_full_name', lambda: context['user'].username)()
            worksheet.write(row, 0, 'Généré par:', header_format)
            worksheet.write(row, 1, user_name or context['user'].username, cell_format)
            row += 1
        
        if context.get('maison'):
            worksheet.write(row, 0, 'Maison:', header_format)
            worksheet.write(row, 1, context['maison'].nom, cell_format)
            row += 1
            worksheet.write(row, 0, 'Adresse:', header_format)
            worksheet.write(row, 1, context['maison'].adresse or 'Non renseignée', cell_format)
            row += 1
        
        worksheet.write(row, 0, 'Nombre de meubles:', header_format)
        worksheet.write(row, 1, context['meubles'].count(), cell_format)
        row += 2
        
        # En-têtes du tableau principal
        headers = ['Nom', 'Numéro de série', 'Type', 'Pièce', 'État', 'Date d\'entrée', 'Dernière vérification', 'Valeur estimée']
        if not context.get('maison'):
            headers.insert(2, 'Maison')
        
        col = 0
        for header in headers:
            worksheet.write(row, col, header, header_format)
            col += 1
        
        # Largeurs des colonnes
        if context.get('maison'):
            widths = [20, 15, 15, 12, 12, 12, 15, 15]
        else:
            widths = [20, 15, 15, 15, 12, 12, 12, 15, 15]
        
        for i, width in enumerate(widths):
            worksheet.set_column(i, i, width)
        
        # Données des meubles
        row += 1
        for meuble in context['meubles']:
            col = 0
            worksheet.write(row, col, meuble.nom, cell_format)
            col += 1
            worksheet.write(row, col, meuble.numero_serie, cell_format)
            col += 1
            
            if not context.get('maison'):
                worksheet.write(row, col, meuble.maison.nom, cell_format)
                col += 1
            
            worksheet.write(row, col, meuble.type_meuble.nom if meuble.type_meuble else 'Non défini', cell_format)
            col += 1
            worksheet.write(row, col, meuble.get_piece_display(), cell_format)
            col += 1
            worksheet.write(row, col, meuble.get_etat_display(), cell_format)
            col += 1
            worksheet.write(row, col, meuble.date_entree, date_format)
            col += 1
            
            if hasattr(meuble, 'date_derniere_verification') and meuble.date_derniere_verification:
                worksheet.write(row, col, meuble.date_derniere_verification, date_format)
            else:
                worksheet.write(row, col, 'Jamais', cell_format)
            col += 1
            
            # Valeur
            if hasattr(meuble, 'valeur_actuelle') and meuble.valeur_actuelle:
                worksheet.write(row, col, float(meuble.valeur_actuelle), money_format)
            elif hasattr(meuble, 'prix_achat') and meuble.prix_achat:
                worksheet.write(row, col, float(meuble.prix_achat), money_format)
            else:
                worksheet.write(row, col, 'Non évaluée', cell_format)
            
            row += 1
        
        # Feuille statistiques
        stats_sheet = workbook.add_worksheet('Statistiques')
        
        # Titre
        stats_sheet.merge_range('A1:C1', 'Statistiques par État', title_format)
        stats_sheet.set_row(0, 25)
        
        # Calculer les statistiques
        meubles = context['meubles']
        total = meubles.count()
        
        if total > 0:
            # En-têtes
            stats_sheet.write(2, 0, 'État', header_format)
            stats_sheet.write(2, 1, 'Nombre', header_format)
            stats_sheet.write(2, 2, 'Pourcentage', header_format)
            
            # Données
            etats = ['bon', 'usage', 'defectueux', 'hors_service']
            etats_labels = {
                'bon': 'Bon état',
                'usage': 'Usagé',
                'defectueux': 'Défectueux',
                'hors_service': 'Hors service'
            }
            
            row = 3
            for etat in etats:
                count = meubles.filter(etat=etat).count()
                pourcentage = (count / total * 100) if total > 0 else 0
                
                stats_sheet.write(row, 0, etats_labels[etat], cell_format)
                stats_sheet.write(row, 1, count, cell_format)
                stats_sheet.write(row, 2, f"{pourcentage:.1f}%", cell_format)
                row += 1
            
            # Total
            stats_sheet.write(row, 0, 'TOTAL', header_format)
            stats_sheet.write(row, 1, total, header_format)
            stats_sheet.write(row, 2, '100%', header_format)
            
            # Largeurs des colonnes
            stats_sheet.set_column(0, 0, 15)
            stats_sheet.set_column(1, 1, 10)
            stats_sheet.set_column(2, 2, 12)
        
        # Répartition par pièce
        pieces_sheet = workbook.add_worksheet('Par Pièce')
        pieces_sheet.merge_range('A1:C1', 'Répartition par Pièce', title_format)
        pieces_sheet.set_row(0, 25)
        
        pieces_sheet.write(2, 0, 'Pièce', header_format)
        pieces_sheet.write(2, 1, 'Nombre', header_format)
        pieces_sheet.write(2, 2, 'Pourcentage', header_format)
        
        # Grouper par pièce
        from django.db.models import Count
        pieces_stats = meubles.values('piece').annotate(count=Count('id')).order_by('-count')
        
        row = 3
        for piece_stat in pieces_stats:
            piece_display = dict(meubles.model.PIECE_CHOICES).get(piece_stat['piece'], piece_stat['piece'])
            count = piece_stat['count']
            pourcentage = (count / total * 100) if total > 0 else 0
            
            pieces_sheet.write(row, 0, piece_display, cell_format)
            pieces_sheet.write(row, 1, count, cell_format)
            pieces_sheet.write(row, 2, f"{pourcentage:.1f}%", cell_format)
            row += 1
        
        pieces_sheet.set_column(0, 0, 15)
        pieces_sheet.set_column(1, 1, 10)
        pieces_sheet.set_column(2, 2, 12)
        
        # Fermer le classeur
        workbook.close()
        
        # Écrire dans la réponse
        output.seek(0)
        response.write(output.getvalue())
        output.close()
        
        return response
        
    except Exception as e:
        print(f"Erreur génération Excel: {e}")
        raise


@login_required
@gestionnaire_required
def generer_rapport(request):
    """Générer des rapports avec support PDF, Excel, CSV et HTML"""
    
    if request.method == 'POST':
        try:
            # Récupérer les paramètres du formulaire
            type_rapport = request.POST.get('type_rapport', 'inventaire')
            format_export = request.POST.get('format_export', 'html')
            maison_id = request.POST.get('maison')
            date_debut = request.POST.get('date_debut')
            date_fin = request.POST.get('date_fin')
            
            # Validation des paramètres
            if not type_rapport:
                messages.error(request, "Type de rapport requis")
                return redirect('meubles:generer_rapport')
            
            # Permissions et queryset de base
            permission_mixin = PermissionMixin()
            permission_mixin.request = request
            
            if hasattr(request.user, 'is_super_admin') and request.user.is_super_admin():
                meubles_base = Meuble.objects.select_related('maison', 'type_meuble', 'ajoute_par')
            else:
                meubles_base = Meuble.objects.filter(maison__gestionnaire=request.user).select_related('maison', 'type_meuble', 'ajoute_par')
            
            # Filtrer par maison si spécifié
            maison = None
            if maison_id:
                try:
                    maison = get_object_or_404(Maison, id=maison_id)
                    if not permission_mixin.can_manage_object(maison):
                        messages.error(request, "Vous n'avez pas accès à cette maison")
                        return redirect('meubles:generer_rapport')
                    meubles_base = meubles_base.filter(maison=maison)
                except Exception:
                    messages.error(request, "Maison invalide")
                    return redirect('meubles:generer_rapport')
            
            # Filtrer par dates si spécifiées
            if date_debut:
                try:
                    meubles_base = meubles_base.filter(date_entree__gte=date_debut)
                except Exception:
                    messages.error(request, "Date de début invalide")
                    return redirect('meubles:generer_rapport')
            
            if date_fin:
                try:
                    meubles_base = meubles_base.filter(date_entree__lte=date_fin)
                except Exception:
                    messages.error(request, "Date de fin invalide")
                    return redirect('meubles:generer_rapport')
            
            # Appliquer les filtres selon le type de rapport
            if type_rapport == 'defectueux':
                meubles = meubles_base.filter(etat='defectueux')
                titre_rapport = 'Meubles Défectueux'
            elif type_rapport == 'verification':
                cutoff_date = timezone.now().date() - timedelta(days=180)
                meubles = meubles_base.filter(
                    Q(date_derniere_verification__isnull=True) |
                    Q(date_derniere_verification__lt=cutoff_date)
                )
                titre_rapport = 'Meubles à Vérifier'
            elif type_rapport == 'valeur':
                meubles = meubles_base.exclude(
                    Q(prix_achat__isnull=True) & Q(valeur_actuelle__isnull=True)
                )
                titre_rapport = 'Évaluation Financière'
            elif type_rapport == 'historique':
                meubles = meubles_base.all()
                titre_rapport = 'Historique des États'
            else:  # inventaire par défaut
                meubles = meubles_base.all()
                titre_rapport = 'Inventaire Complet'
            
            # Vérifier qu'il y a des résultats
            if not meubles.exists():
                messages.warning(request, f"Aucun meuble trouvé pour le rapport '{titre_rapport}'")
                return redirect('meubles:generer_rapport')
            
            # Préparer le contexte enrichi
            context = {
                'meubles': meubles,
                'type_rapport': titre_rapport,
                'maison': maison,
                'date_generation': timezone.now(),
                'user': request.user,
                'request': request,
                'date_debut': date_debut,
                'date_fin': date_fin,
                'format_export': format_export,
                'total_meubles': meubles.count(),
            }
            
            # Ajouter des statistiques au contexte
            try:
                context['stats'] = {
                    'total': meubles.count(),
                    'bon_etat': meubles.filter(etat='bon').count(),
                    'usage': meubles.filter(etat='usage').count(),
                    'defectueux': meubles.filter(etat='defectueux').count(),
                    'hors_service': meubles.filter(etat='hors_service').count(),
                }
            except Exception:
                context['stats'] = {'total': meubles.count()}
            
            # Générer selon le format demandé
            if format_export == 'pdf':
                return generer_pdf_rapport(context, titre_rapport)
            elif format_export == 'excel':
                return generer_excel_rapport(context, titre_rapport)
            elif format_export == 'csv':
                # Pour CSV, on passe les paramètres via GET pour réutiliser la fonction existante
                request.GET = request.GET.copy()
                request.GET['type_rapport'] = type_rapport
                if maison_id:
                    request.GET['maison'] = maison_id
                return export_meubles_csv(request)
            else:  # HTML par défaut
                return render(request, 'meubles/rapports/rapport.html', context)
                
        except Exception as e:
            messages.error(request, f"Erreur lors de la génération du rapport: {str(e)}")
            print(f"Erreur génération rapport: {e}")  # Pour le debug
            return redirect('meubles:generer_rapport')
    
    else:
        # Afficher le formulaire de sélection de rapport
        try:
            from .forms import RapportMeublesForm
            form = RapportMeublesForm(user=request.user)
            
            # Ajouter des statistiques pour guider l'utilisateur
            if hasattr(request.user, 'is_super_admin') and request.user.is_super_admin():
                meubles_base = Meuble.objects.all()
            else:
                meubles_base = Meuble.objects.filter(maison__gestionnaire=request.user)
            
            context_stats = {
                'total_meubles': meubles_base.count(),
                'meubles_defectueux': meubles_base.filter(etat='defectueux').count(),
                'meubles_bon_etat': meubles_base.filter(etat='bon').count(),
            }
            
            # Meubles à vérifier
            try:
                cutoff_date = timezone.now().date() - timedelta(days=180)
                context_stats['meubles_a_verifier'] = meubles_base.filter(
                    Q(date_derniere_verification__isnull=True) |
                    Q(date_derniere_verification__lt=cutoff_date)
                ).count()
            except:
                context_stats['meubles_a_verifier'] = 0
            
            context = {
                'form': form,
                'stats': context_stats,
            }
            
            return render(request, 'meubles/rapports/form.html', context)
            
        except Exception as e:
            messages.error(request, f"Erreur lors du chargement du formulaire: {str(e)}")
            return redirect('meubles:dashboard') 

def generer_pdf_rapport_simplifie(context, titre_rapport):
    """Version simplifiée de la génération PDF sans PageBreak"""
    try:
        # Créer la réponse HTTP
        response = HttpResponse(content_type='application/pdf')
        filename = f"rapport_{titre_rapport.lower().replace(' ', '_')}_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Créer le document PDF
        doc = SimpleDocTemplate(
            response, 
            pagesize=A4,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch
        )
        story = []
        styles = getSampleStyleSheet()
        
        # Style pour le titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f2937'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        # Style pour les sections
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#374151'),
            spaceBefore=20,
            spaceAfter=10
        )
        
        # Titre principal
        story.append(Paragraph(f"<b>{context['type_rapport']}</b>", title_style))
        
        # Informations sur le rapport
        info_data = [
            ['Date de génération:', context['date_generation'].strftime('%d/%m/%Y à %H:%M')],
        ]
        
        # Utilisateur avec gestion sécurisée
        user = context.get('user')
        if user:
            user_name = get_user_display_name(user)
            info_data.append(['Généré par:', user_name])
        
        if context.get('maison'):
            info_data.extend([
                ['Maison:', context['maison'].nom],
                ['Adresse:', getattr(context['maison'], 'adresse', '') or 'Non renseignée'],
            ])
        
        info_data.append(['Nombre de meubles:', str(context['meubles'].count())])
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Statistiques par état
        meubles = context['meubles']
        total_meubles = meubles.count()
        
        if total_meubles > 0:
            story.append(Paragraph("Statistiques par État", section_style))
            
            # Calculer les statistiques
            try:
                bon_etat = meubles.filter(etat='bon').count()
                defectueux = meubles.filter(etat='defectueux').count()
                usage = meubles.filter(etat='usage').count()
                hors_service = meubles.filter(etat='hors_service').count()
                
                stats_data = [
                    ['État', 'Nombre', 'Pourcentage'],
                    ['Bon état', str(bon_etat), f"{(bon_etat/total_meubles*100):.1f}%"],
                    ['Usagé', str(usage), f"{(usage/total_meubles*100):.1f}%"],
                    ['Défectueux', str(defectueux), f"{(defectueux/total_meubles*100):.1f}%"],
                    ['Hors service', str(hors_service), f"{(hors_service/total_meubles*100):.1f}%"],
                    ['TOTAL', str(total_meubles), '100%']
                ]
                
                stats_table = Table(stats_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
                stats_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ]))
                story.append(stats_table)
                story.append(Spacer(1, 20))
                
            except Exception as e:
                print(f"Erreur calcul statistiques: {e}")
        
        # Ajouter un espacement avant le tableau principal
        story.append(Spacer(1, 20))
        
        # Tableau principal des meubles
        if context['meubles'].exists():
            story.append(Paragraph("Liste des Meubles", section_style))
            
            # Limiter à 50 meubles pour le PDF
            meubles_limit = context['meubles'][:50]
            
            # En-têtes du tableau
            if context.get('maison'):
                headers = ['Nom', 'Type', 'Pièce', 'État', 'Date entrée']
                col_widths = [2.5*inch, 1.5*inch, 1.2*inch, 1*inch, 1.3*inch]
            else:
                headers = ['Nom', 'Maison', 'Type', 'Pièce', 'État']
                col_widths = [2*inch, 1.5*inch, 1.2*inch, 1*inch, 1*inch]
            
            # Données du tableau
            table_data = [headers]
            
            for meuble in meubles_limit:
                try:
                    nom = str(getattr(meuble, 'nom', 'Sans nom'))
                    
                    type_meuble = 'N/D'
                    if hasattr(meuble, 'type_meuble') and meuble.type_meuble:
                        type_meuble = str(getattr(meuble.type_meuble, 'nom', 'N/D'))
                    
                    # Pièce
                    try:
                        if hasattr(meuble, 'get_piece_display'):
                            piece = meuble.get_piece_display()
                        else:
                            piece = str(getattr(meuble, 'piece', 'N/D'))
                    except:
                        piece = 'N/D'
                    
                    # État
                    try:
                        if hasattr(meuble, 'get_etat_display'):
                            etat = meuble.get_etat_display()
                        else:
                            etat = str(getattr(meuble, 'etat', 'N/D'))
                    except:
                        etat = 'N/D'
                    
                    # Date d'entrée
                    date_entree = 'N/D'
                    if hasattr(meuble, 'date_entree') and meuble.date_entree:
                        try:
                            date_entree = meuble.date_entree.strftime('%d/%m/%Y')
                        except:
                            date_entree = 'N/D'
                    
                    if context.get('maison'):
                        row = [nom, type_meuble, piece, etat, date_entree]
                    else:
                        maison_nom = 'N/D'
                        if hasattr(meuble, 'maison') and meuble.maison:
                            maison_nom = str(getattr(meuble.maison, 'nom', 'N/D'))
                        row = [nom, maison_nom, type_meuble, piece, etat]
                    
                    table_data.append(row)
                    
                except Exception as e:
                    print(f"Erreur traitement meuble PDF: {e}")
                    continue
            
            # Créer le tableau
            main_table = Table(table_data, colWidths=col_widths)
            main_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ]))
            story.append(main_table)
            
            # Note si plus de 50 meubles
            if context['meubles'].count() > 50:
                story.append(Spacer(1, 10))
                note_style = ParagraphStyle(
                    'Note',
                    parent=styles['Normal'],
                    fontSize=9,
                    textColor=colors.HexColor('#6b7280'),
                    alignment=TA_CENTER,
                    fontName='Helvetica-Oblique'
                )
                story.append(Paragraph(
                    f"<i>Note: Seuls les 50 premiers meubles sont affichés. Total: {context['meubles'].count()}.</i>",
                    note_style
                ))
        
        # Pied de page
        story.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#6b7280'),
            alignment=TA_CENTER
        )
        
        footer_text = f"RepAvi Lodges - Rapport généré le {context['date_generation'].strftime('%d/%m/%Y à %H:%M')}"
        user = context.get('user')
        if user:
            user_name = get_user_display_name(user)
            footer_text += f" par {user_name}"
        
        story.append(Paragraph(footer_text, footer_style))
        
        # Construire le PDF
        doc.build(story)
        return response
        
    except Exception as e:
        print(f"Erreur génération PDF simplifiée: {e}")
        import traceback
        traceback.print_exc()
        
        # PDF d'erreur minimal
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="erreur_rapport.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=A4)
        styles = getSampleStyleSheet()
        
        error_story = [
            Paragraph("Erreur de génération du rapport", styles['Title']),
            Paragraph(f"Détail de l'erreur: {str(e)}", styles['Normal']),
            Paragraph("Veuillez contacter l'administrateur système.", styles['Normal'])
        ]
        
        doc.build(error_story)
        return response

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


# === FONCTIONS UTILITAIRES POUR LES EXPORTS ===

def generer_rapport_simple_csv(meubles, filename_prefix="meubles"):
    """Fonction utilitaire pour générer un CSV simple"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    timestamp = timezone.now().strftime("%Y%m%d_%H%M")
    response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{timestamp}.csv"'
    
    # BOM UTF-8
    response.write('\ufeff')
    
    writer = csv.writer(response, delimiter=';')
    
    # En-têtes simplifiés
    headers = ['Nom', 'Type', 'Pièce', 'État', 'Maison', 'Date entrée']
    writer.writerow(headers)
    
    # Données
    for meuble in meubles:
        row = [
            meuble.nom or '',
            meuble.type_meuble.nom if meuble.type_meuble else '',
            meuble.get_piece_display() if hasattr(meuble, 'get_piece_display') else '',
            meuble.get_etat_display() if hasattr(meuble, 'get_etat_display') else meuble.etat,
            meuble.maison.nom if meuble.maison else '',
            meuble.date_entree.strftime('%d/%m/%Y') if meuble.date_entree else ''
        ]
        writer.writerow(row)
    
    return response


@login_required
@gestionnaire_required
def export_rapport_rapide(request, type_rapport):
    """Export rapide sans formulaire"""
    try:
        # Permissions
        if hasattr(request.user, 'is_super_admin') and request.user.is_super_admin():
            meubles_base = Meuble.objects.select_related('maison', 'type_meuble')
        else:
            meubles_base = Meuble.objects.filter(maison__gestionnaire=request.user).select_related('maison', 'type_meuble')
        
        # Filtres selon le type
        if type_rapport == 'defectueux':
            meubles = meubles_base.filter(etat='defectueux')
            titre = 'Meubles Défectueux'
        elif type_rapport == 'verification':
            cutoff_date = timezone.now().date() - timedelta(days=180)
            meubles = meubles_base.filter(
                Q(date_derniere_verification__isnull=True) |
                Q(date_derniere_verification__lt=cutoff_date)
            )
            titre = 'Meubles à Vérifier'
        elif type_rapport == 'bon_etat':
            meubles = meubles_base.filter(etat='bon')
            titre = 'Meubles en Bon État'
        else:
            meubles = meubles_base.all()
            titre = 'Inventaire Complet'
        
        if not meubles.exists():
            messages.warning(request, f"Aucun meuble trouvé pour '{titre}'")
            return redirect('meubles:dashboard')
        
        # Context pour le rapport
        context = {
            'meubles': meubles,
            'type_rapport': titre,
            'date_generation': timezone.now(),
            'user': request.user,
        }
        
        # Format par défaut: HTML
        format_export = request.GET.get('format', 'html')
        
        if format_export == 'pdf':
            return generer_pdf_rapport(context, titre)
        elif format_export == 'excel':
            return generer_excel_rapport(context, titre)
        elif format_export == 'csv':
            return generer_rapport_simple_csv(meubles, type_rapport)
        else:
            return render(request, 'meubles/rapports/rapport.html', context)
            
    except Exception as e:
        messages.error(request, f"Erreur lors de l'export: {str(e)}")
        return redirect('meubles:dashboard')


@login_required
@gestionnaire_required  
def preview_rapport_ajax(request):
    """Aperçu AJAX d'un rapport avant génération"""
    try:
        type_rapport = request.GET.get('type_rapport', 'inventaire')
        maison_id = request.GET.get('maison')
        
        # Base queryset
        if hasattr(request.user, 'is_super_admin') and request.user.is_super_admin():
            meubles_base = Meuble.objects.select_related('maison', 'type_meuble')
        else:
            meubles_base = Meuble.objects.filter(maison__gestionnaire=request.user).select_related('maison', 'type_meuble')
        
        # Filtrer par maison
        if maison_id:
            meubles_base = meubles_base.filter(maison_id=maison_id)
        
        # Appliquer filtres selon type
        if type_rapport == 'defectueux':
            meubles = meubles_base.filter(etat='defectueux')
        elif type_rapport == 'verification':
            cutoff_date = timezone.now().date() - timedelta(days=180)
            meubles = meubles_base.filter(
                Q(date_derniere_verification__isnull=True) |
                Q(date_derniere_verification__lt=cutoff_date)
            )
        elif type_rapport == 'valeur':
            meubles = meubles_base.exclude(
                Q(prix_achat__isnull=True) & Q(valeur_actuelle__isnull=True)
            )
        else:
            meubles = meubles_base.all()
        
        # Statistiques pour l'aperçu
        stats = {
            'total': meubles.count(),
            'bon_etat': meubles.filter(etat='bon').count(),
            'defectueux': meubles.filter(etat='defectueux').count(),
            'usage': meubles.filter(etat='usage').count(),
        }
        
        # Échantillon de meubles
        echantillon = list(meubles[:5].values(
            'nom', 'type_meuble__nom', 'etat', 'maison__nom'
        ))
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'echantillon': echantillon,
            'message': f"Aperçu pour {stats['total']} meuble(s)"
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })