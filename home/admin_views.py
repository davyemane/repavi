# home/admin_views.py - VERSION FINALE CORRIGÉE pour Dashboard

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.urls import reverse
from django.core.exceptions import PermissionDenied, ValidationError
from django import forms
from django.views.decorators.http import require_http_methods
from django.db import transaction
from datetime import datetime, timedelta
from django.utils.text import slugify

# Import sécurisé des décorateurs
try:
    from utils.decorators import gestionnaire_required, super_admin_required, role_required
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
    
    def role_required(roles):
        def decorator(func):
            return gestionnaire_required(func)
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
    print("⚠️ Services non disponibles - utilisation des fallbacks")

from .models import Ville, CategorieMaison, Maison, PhotoMaison, Reservation
from .forms import (
    VilleForm, CategorieMaisonForm, MaisonForm, 
    PhotoMaisonForm, ReservationForm, MaisonFilterForm
)

# ======== DASHBOARD PRINCIPAL ========

@login_required
@gestionnaire_required
def admin_dashboard(request):
    """Tableau de bord principal de l'administration - VERSION COMPLÈTE"""
    
    # Utiliser le service de statistiques avec fallback
    if SERVICES_AVAILABLE:
        try:
            stats = StatisticsService.get_dashboard_stats(request.user)
        except Exception as e:
            print(f"Erreur service statistiques: {e}")
            stats = _get_fallback_stats(request.user)
    else:
        stats = _get_fallback_stats(request.user)
    
    # Dernières maisons ajoutées
    try:
        dernieres_maisons = Maison.objects.accessible_to_user(request.user).select_related('ville', 'categorie', 'gestionnaire').prefetch_related('photos')[:5]
    except Exception as e:
        print(f"Erreur requête maisons: {e}")
        dernieres_maisons = _get_fallback_maisons(request.user)[:5]
    
    # Dernières réservations
    if SERVICES_AVAILABLE:
        try:
            dernieres_reservations = ReservationService.get_reservations_for_user(request.user)[:5]
        except Exception:
            dernieres_reservations = _get_fallback_reservations(request.user)[:5]
    else:
        dernieres_reservations = _get_fallback_reservations(request.user)[:5]
    
    # Activités récentes
    activites_recentes = _get_recent_activities(request.user)
    
    # Maisons populaires
    try:
        if hasattr(request.user, 'is_super_admin') and request.user.is_super_admin():
            maisons_populaires = Maison.objects.annotate(
                nb_reservations=Count('reservations')
            ).order_by('-nb_reservations')[:5]
        else:
            maisons_populaires = Maison.objects.filter(
                gestionnaire=request.user
            ).annotate(
                nb_reservations=Count('reservations')
            ).order_by('-nb_reservations')[:5]
    except Exception:
        maisons_populaires = _get_fallback_maisons(request.user)[:5]
    
    # Déterminer les permissions de manière robuste
    is_super_admin = False
    is_gestionnaire = False
    
    # Vérifier le rôle super admin
    if hasattr(request.user, 'role') and request.user.role == 'SUPER_ADMIN':
        is_super_admin = True
    elif request.user.is_superuser:
        is_super_admin = True
    elif hasattr(request.user, 'is_super_admin') and callable(request.user.is_super_admin) and request.user.is_super_admin():
        is_super_admin = True
    
    # Vérifier le rôle gestionnaire
    if hasattr(request.user, 'role') and request.user.role == 'GESTIONNAIRE':
        is_gestionnaire = True
    elif request.user.is_staff and not request.user.is_superuser:
        is_gestionnaire = True
    elif hasattr(request.user, 'is_gestionnaire') and callable(request.user.is_gestionnaire) and request.user.is_gestionnaire():
        is_gestionnaire = True
    
    # Tout utilisateur staff peut créer (sauf restriction spécifique)
    can_create = is_super_admin or is_gestionnaire or request.user.is_staff
    
    context = {
        'stats': stats,
        'dernieres_maisons': dernieres_maisons,
        'dernieres_reservations': dernieres_reservations,
        'maisons_populaires': maisons_populaires,
        'activites_recentes': activites_recentes,
        'user_role': getattr(request.user, 'role', 'unknown'),
        'is_gestionnaire': is_gestionnaire,
        'is_super_admin': is_super_admin,
        'can_create': can_create,
        'can_delete': is_super_admin,
    }
    
    return render(request, 'admin/dashboard.html', context)

# ======== FONCTIONS HELPER AMÉLIORÉES ========

def _get_fallback_stats(user):
    """Statistiques de fallback en cas d'erreur des services"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            # Stats globales pour super admin
            total_maisons = Maison.objects.count()
            maisons_disponibles = Maison.objects.filter(disponible=True).count()
            maisons_featured = Maison.objects.filter(featured=True).count()
            
            total_reservations = Reservation.objects.count()
            reservations_en_attente = Reservation.objects.filter(statut='en_attente').count()
            reservations_confirmees = Reservation.objects.filter(statut='confirmee').count()
            
            # Stats utilisateurs
            total_users = User.objects.count()
            users_actifs = User.objects.filter(is_active=True).count()
            
            try:
                total_clients = User.objects.filter(role='CLIENT').count()
                total_gestionnaires = User.objects.filter(role='GESTIONNAIRE').count()
                total_admins = User.objects.filter(role='SUPER_ADMIN').count()
            except:
                total_clients = User.objects.filter(is_staff=False, is_superuser=False).count()
                total_gestionnaires = User.objects.filter(is_staff=True, is_superuser=False).count()
                total_admins = User.objects.filter(is_superuser=True).count()
            
            # Stats photos
            total_photos = PhotoMaison.objects.count()
            photos_principales = PhotoMaison.objects.filter(principale=True).count()
            
        else:
            # Stats pour gestionnaire
            maisons_user = Maison.objects.filter(gestionnaire=user)
            total_maisons = maisons_user.count()
            maisons_disponibles = maisons_user.filter(disponible=True).count()
            maisons_featured = maisons_user.filter(featured=True).count()
            
            reservations_user = Reservation.objects.filter(maison__gestionnaire=user)
            total_reservations = reservations_user.count()
            reservations_en_attente = reservations_user.filter(statut='en_attente').count()
            reservations_confirmees = reservations_user.filter(statut='confirmee').count()
            
            # Stats photos pour ce gestionnaire
            total_photos = PhotoMaison.objects.filter(maison__gestionnaire=user).count()
            photos_principales = PhotoMaison.objects.filter(maison__gestionnaire=user, principale=True).count()
            
            # Pas d'accès aux stats utilisateurs pour les gestionnaires
            total_users = 0
            users_actifs = 0
            total_clients = 0
            total_gestionnaires = 0
            total_admins = 0
        
        # Calcul du CA mensuel
        debut_mois = datetime.now().replace(day=1)
        ca_query = Reservation.objects.filter(
            date_creation__gte=debut_mois,
            statut='confirmee'
        )
        
        if not (hasattr(user, 'is_super_admin') and user.is_super_admin()):
            ca_query = ca_query.filter(maison__gestionnaire=user)
        
        ca_mensuel = ca_query.aggregate(total=Sum('prix_total'))['total'] or 0
        
        # Calcul évolution CA (mois précédent)
        debut_mois_precedent = (debut_mois - timedelta(days=1)).replace(day=1)
        fin_mois_precedent = debut_mois - timedelta(days=1)
        
        ca_precedent_query = Reservation.objects.filter(
            date_creation__gte=debut_mois_precedent,
            date_creation__lte=fin_mois_precedent,
            statut='confirmee'
        )
        
        if not (hasattr(user, 'is_super_admin') and user.is_super_admin()):
            ca_precedent_query = ca_precedent_query.filter(maison__gestionnaire=user)
        
        ca_precedent = ca_precedent_query.aggregate(total=Sum('prix_total'))['total'] or 0
        
        # Évolution en pourcentage
        if ca_precedent > 0:
            evolution_ca = round(((ca_mensuel - ca_precedent) / ca_precedent) * 100, 1)
        else:
            evolution_ca = 100 if ca_mensuel > 0 else 0
        
        return {
            'total_maisons': total_maisons,
            'maisons_disponibles': maisons_disponibles,
            'maisons_featured': maisons_featured,
            'total_reservations': total_reservations,
            'reservations_en_attente': reservations_en_attente,
            'reservations_confirmees': reservations_confirmees,
            'total_users': total_users,
            'users_actifs': users_actifs,
            'total_clients': total_clients,
            'total_gestionnaires': total_gestionnaires,
            'total_admins': total_admins,
            'total_photos': total_photos,
            'photos_principales': photos_principales,
            'ca_mensuel': float(ca_mensuel),
            'evolution_ca': evolution_ca,
        }
    except Exception as e:
        print(f"Erreur fallback stats: {e}")
        return {
            'total_maisons': 0,
            'maisons_disponibles': 0,
            'maisons_featured': 0,
            'total_reservations': 0,
            'reservations_en_attente': 0,
            'reservations_confirmees': 0,
            'total_users': 0,
            'users_actifs': 0,
            'total_clients': 0,
            'total_gestionnaires': 0,
            'total_admins': 0,
            'total_photos': 0,
            'photos_principales': 0,
            'ca_mensuel': 0,
            'evolution_ca': 0,
        }

def _get_fallback_maisons(user):
    """Maisons de fallback"""
    try:
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            return Maison.objects.all().select_related('ville', 'categorie', 'gestionnaire')
        elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
            return Maison.objects.filter(gestionnaire=user).select_related('ville', 'categorie')
        else:
            return Maison.objects.filter(disponible=True).select_related('ville', 'categorie', 'gestionnaire')
    except Exception:
        return Maison.objects.none()

def _get_fallback_reservations(user):
    """Réservations de fallback"""
    try:
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            return Reservation.objects.all().select_related('maison', 'client').order_by('-date_creation')
        elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
            return Reservation.objects.filter(maison__gestionnaire=user).select_related('maison', 'client').order_by('-date_creation')
        else:
            return Reservation.objects.filter(client=user).select_related('maison').order_by('-date_creation')
    except Exception:
        return Reservation.objects.none()

def _get_recent_activities(user):
    """Récupère les activités récentes avec plus de détails"""
    activities = []
    
    try:
        # Dernières maisons créées
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            maisons_recentes = Maison.objects.all().order_by('-date_creation')[:3]
        else:
            maisons_recentes = Maison.objects.filter(gestionnaire=user).order_by('-date_creation')[:3]
        
        for maison in maisons_recentes:
            gestionnaire_name = maison.gestionnaire.first_name or maison.gestionnaire.username
            activities.append({
                'description': f'<strong>{gestionnaire_name}</strong> a ajouté la maison <strong>{maison.nom}</strong> à {maison.ville.nom}',
                'date': maison.date_creation,
                'icone': 'home',
                'couleur': 'blue'
            })
        
        # Dernières réservations
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            reservations_recentes = Reservation.objects.all().order_by('-date_creation')[:3]
        else:
            reservations_recentes = Reservation.objects.filter(maison__gestionnaire=user).order_by('-date_creation')[:3]
        
        for reservation in reservations_recentes:
            client_name = reservation.client.first_name or reservation.client.username
            activities.append({
                'description': f'<strong>{client_name}</strong> a réservé <strong>{reservation.maison.nom}</strong> du {reservation.date_debut.strftime("%d/%m")} au {reservation.date_fin.strftime("%d/%m")}',
                'date': reservation.date_creation,
                'icone': 'calendar-check',
                'couleur': 'green'
            })
        
        # Dernières photos ajoutées
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            photos_recentes = PhotoMaison.objects.all().order_by('-id')[:2]
        else:
            photos_recentes = PhotoMaison.objects.filter(maison__gestionnaire=user).order_by('-id')[:2]
        
        for photo in photos_recentes:
            activities.append({
                'description': f'Nouvelle photo ajoutée pour <strong>{photo.maison.nom}</strong>',
                'date': photo.maison.date_modification,
                'icone': 'camera',
                'couleur': 'purple'
            })
        
        # Confirmations de réservations récentes
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            confirmations_recentes = Reservation.objects.filter(statut='confirmee').order_by('-date_modification')[:2]
        else:
            confirmations_recentes = Reservation.objects.filter(maison__gestionnaire=user, statut='confirmee').order_by('-date_modification')[:2]
        
        for confirmation in confirmations_recentes:
            client_name = confirmation.client.first_name or confirmation.client.username
            activities.append({
                'description': f'Réservation confirmée : <strong>{client_name}</strong> pour <strong>{confirmation.maison.nom}</strong>',
                'date': confirmation.date_modification,
                'icone': 'check-circle',
                'couleur': 'green'
            })
        
        # Trier par date
        activities.sort(key=lambda x: x['date'], reverse=True)
        
    except Exception as e:
        print(f"Erreur activités récentes: {e}")
    
    return activities[:10]

# ======== GESTION DES UTILISATEURS ========

@login_required
@super_admin_required
def admin_users_list(request):
    """Liste des utilisateurs avec filtres - SUPER ADMIN SEULEMENT"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    role_filter = request.GET.get('role', '')
    search = request.GET.get('search', '')
    
    users = User.objects.all()
    
    if role_filter:
        try:
            users = users.filter(role=role_filter)
        except:
            # Fallback si pas de champ role
            if role_filter == 'SUPER_ADMIN':
                users = users.filter(is_superuser=True)
            elif role_filter == 'GESTIONNAIRE':
                users = users.filter(is_staff=True, is_superuser=False)
            else:  # CLIENT
                users = users.filter(is_staff=False, is_superuser=False)
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    users = users.order_by('-date_joined')
    
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Déterminer les rôles disponibles
    try:
        roles = getattr(User, 'ROLE_CHOICES', [
            ('CLIENT', 'Client'),
            ('GESTIONNAIRE', 'Gestionnaire'),
            ('SUPER_ADMIN', 'Super Admin')
        ])
    except:
        roles = [
            ('CLIENT', 'Client'),
            ('GESTIONNAIRE', 'Gestionnaire'),
            ('SUPER_ADMIN', 'Super Admin')
        ]
    
    context = {
        'page_obj': page_obj,
        'role_filter': role_filter,
        'search': search,
        'roles': roles,
    }
    
    return render(request, 'users/list.html', context)

@login_required
@super_admin_required
@require_http_methods(["POST"])
def admin_create_client(request):
    """Créer un nouveau client via AJAX - SUPER ADMIN SEULEMENT"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        with transaction.atomic():
            # Créer l'utilisateur
            user_data = {
                'username': request.POST.get('username'),
                'email': request.POST.get('email'),
                'first_name': request.POST.get('first_name'),
                'last_name': request.POST.get('last_name'),
                'password': request.POST.get('password'),
                'is_active': True,
            }
            
            # Ajouter le téléphone si le champ existe
            telephone = request.POST.get('telephone', '')
            if hasattr(User, 'telephone'):
                user_data['telephone'] = telephone
            
            # Gérer le rôle selon le modèle User
            if hasattr(User, 'role'):
                user_data['role'] = 'CLIENT'
                user_data['email_verifie'] = True  # Créé par admin, donc vérifié
            
            user = User.objects.create_user(**user_data)
            
            # Créer le profil client si disponible
            try:
                from users.models import ProfilClient
                ProfilClient.objects.create(user=user)
            except ImportError:
                pass
            
            return JsonResponse({
                'success': True,
                'message': f'Client {user.first_name} {user.last_name} créé avec succès'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@super_admin_required
@require_http_methods(["POST"])
def admin_create_gestionnaire(request):
    """Créer un nouveau gestionnaire via AJAX - SUPER ADMIN SEULEMENT"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        with transaction.atomic():
            # Créer l'utilisateur
            user_data = {
                'username': request.POST.get('username'),
                'email': request.POST.get('email'),
                'first_name': request.POST.get('first_name'),
                'last_name': request.POST.get('last_name'),
                'password': request.POST.get('password'),
                'is_active': True,
                'is_staff': True,  # Gestionnaire = staff
            }
            
            # Ajouter le téléphone si le champ existe
            telephone = request.POST.get('telephone', '')
            if hasattr(User, 'telephone'):
                user_data['telephone'] = telephone
            
            # Gérer le rôle selon le modèle User
            if hasattr(User, 'role'):
                user_data['role'] = 'GESTIONNAIRE'
                user_data['email_verifie'] = True  # Créé par admin, donc vérifié
            
            user = User.objects.create_user(**user_data)
            
            # Créer le profil gestionnaire si disponible
            try:
                from users.models import ProfilGestionnaire
                ProfilGestionnaire.objects.create(user=user)
            except ImportError:
                pass
            
            return JsonResponse({
                'success': True,
                'message': f'Gestionnaire {user.first_name} {user.last_name} créé avec succès'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@super_admin_required
def change_user_role_view(request, user_id):
    """Changer le rôle d'un utilisateur - SUPER ADMIN SEULEMENT"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    user_to_modify = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        old_role = getattr(user_to_modify, 'role', 'CLIENT')
        new_role = request.POST.get('role')
        
        # Déterminer les rôles valides
        try:
            valid_roles = [choice[0] for choice in getattr(User, 'ROLE_CHOICES', [])]
        except:
            valid_roles = ['CLIENT', 'GESTIONNAIRE', 'SUPER_ADMIN']
        
        if new_role in valid_roles:
            if old_role != new_role:
                with transaction.atomic():
                    # Mettre à jour le rôle
                    if hasattr(User, 'role'):
                        user_to_modify.role = new_role
                    
                    # Gérer les permissions staff/superuser
                    if new_role == 'SUPER_ADMIN':
                        user_to_modify.is_staff = True
                        user_to_modify.is_superuser = True
                    elif new_role == 'GESTIONNAIRE':
                        user_to_modify.is_staff = True
                        user_to_modify.is_superuser = False
                    else:  # CLIENT
                        user_to_modify.is_staff = False
                        user_to_modify.is_superuser = False
                    
                    user_to_modify.save()
                    
                    # Créer/supprimer les profils étendus selon le nouveau rôle
                    try:
                        from users.models import ProfilGestionnaire, ProfilClient
                        
                        if new_role == 'GESTIONNAIRE' and old_role != 'GESTIONNAIRE':
                            ProfilGestionnaire.objects.get_or_create(user=user_to_modify)
                        elif new_role == 'CLIENT' and old_role != 'CLIENT':
                            ProfilClient.objects.get_or_create(user=user_to_modify)
                    except ImportError:
                        pass
                
                messages.success(request, 
                    f'Rôle de {user_to_modify.first_name} {user_to_modify.last_name} changé de {old_role} à {new_role}.')
            
            return redirect('repavi_admin:users_list')
    
    # Déterminer les rôles disponibles
    try:
        roles = getattr(User, 'ROLE_CHOICES', [
            ('CLIENT', 'Client'),
            ('GESTIONNAIRE', 'Gestionnaire'),
            ('SUPER_ADMIN', 'Super Admin')
        ])
    except:
        roles = [
            ('CLIENT', 'Client'),
            ('GESTIONNAIRE', 'Gestionnaire'),
            ('SUPER_ADMIN', 'Super Admin')
        ]
    
    context = {
        'user_to_modify': user_to_modify,
        'roles': roles,
    }
    
    return render(request, 'users/change_role.html', context)

# ======== GESTION DES VILLES ========

@login_required
@gestionnaire_required
def admin_villes_list(request):
    """Liste des villes - ADAPTÉ"""
    search = request.GET.get('search', '')
    villes = Ville.objects.annotate(nb_maisons=Count('maison'))
    
    # Filtrer selon les permissions
    if not (hasattr(request.user, 'is_super_admin') and request.user.is_super_admin()):
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
        'can_create': hasattr(request.user, 'is_gestionnaire') and request.user.is_gestionnaire(),
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
    if not (hasattr(request.user, 'is_super_admin') and request.user.is_super_admin()):
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
    if not (hasattr(request.user, 'is_super_admin') and request.user.is_super_admin()):
        categories = categories.filter(maison__gestionnaire=request.user).distinct()
    
    categories = categories.order_by('nom')
    
    context = {
        'categories': categories,
        'can_create': hasattr(request.user, 'is_gestionnaire') and request.user.is_gestionnaire(),
        'can_delete': hasattr(request.user, 'is_super_admin') and request.user.is_super_admin(),
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
    """Liste des maisons avec filtres - CORRIGÉ"""
    form = MaisonFilterForm(request.GET)
    
    # Récupérer les maisons avec fallback
    if SERVICES_AVAILABLE:
        try:
            maisons = MaisonService.get_maisons_for_user(request.user)
        except Exception as e:
            print(f"Erreur service maison: {e}")
            maisons = _get_fallback_maisons(request.user)
    else:
        maisons = _get_fallback_maisons(request.user)
    
    # Appliquer les filtres
    if form.is_valid():
        search = form.cleaned_data.get('search')
        ville = form.cleaned_data.get('ville')
        categorie = form.cleaned_data.get('categorie')
        disponible = form.cleaned_data.get('disponible')
        featured = form.cleaned_data.get('featured')
        
        # Filtres de recherche textuelle
        if search:
            maisons = maisons.filter(
                Q(nom__icontains=search) |
                Q(description__icontains=search) |
                Q(ville__nom__icontains=search)
            )
        
        # Autres filtres
        if ville:
            maisons = maisons.filter(ville=ville)
        if categorie:
            maisons = maisons.filter(categorie=categorie)
        if disponible:
            maisons = maisons.filter(disponible=disponible == 'True')
        if featured:
            maisons = maisons.filter(featured=featured == 'True')
    
    # Pagination
    paginator = Paginator(maisons, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'can_create': hasattr(request.user, 'is_gestionnaire') and request.user.is_gestionnaire(),
        'can_delete': hasattr(request.user, 'is_super_admin') and request.user.is_super_admin(),
    }
    
    return render(request, 'admin/maisons/list.html', context)

@login_required
@gestionnaire_required
def admin_maison_create(request):
    if request.method == 'POST':
        form = MaisonForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                maison = form.save()
                messages.success(request, f'La maison "{maison.nom}" a été créée avec succès.')
                return redirect('repavi_admin:maisons_list')
            except Exception as e:
                messages.error(request, f'Erreur lors de la création : {str(e)}')
        else:
            print("Erreurs du formulaire :", form.errors)
    else:
        form = MaisonForm(user=request.user)

    context = {
        'form': form,
        'action': 'Créer'
    }
    return render(request, 'admin/maisons/form.html', context)

@login_required
@gestionnaire_required
def admin_maison_edit(request, pk):
    """Modifier une maison - ADAPTÉ"""
    maison = get_object_or_404(Maison, pk=pk)
    
    # Vérifier les permissions
    if not maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour modifier cette maison.")
        return redirect('repavi_admin:maisons_list')
    
    if request.method == 'POST':
        form = MaisonForm(request.POST, instance=maison, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'La maison "{maison.nom}" a été modifiée avec succès.')
            return redirect('repavi_admin:maisons_list')
    else:
        form = MaisonForm(instance=maison, user=request.user)
    
    context = {'form': form, 'action': 'Modifier', 'objet': maison}
    return render(request, 'admin/maisons/form.html', context)

@login_required
@gestionnaire_required
def admin_maison_delete(request, pk):
    """Supprimer une maison - ADAPTÉ"""
    maison = get_object_or_404(Maison, pk=pk)
    
    if not maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour supprimer cette maison.")
        return redirect('repavi_admin:maisons_list')
    
    if request.method == 'POST':
        nom = maison.nom
        maison.delete()
        messages.success(request, f'La maison "{nom}" a été supprimée avec succès.')
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
    if not (hasattr(request.user, 'is_super_admin') and request.user.is_super_admin()):
        photos = photos.filter(maison__gestionnaire=request.user)
    
    if maison_id:
        photos = photos.filter(maison_id=maison_id)
    
    photos = photos.order_by('maison__nom', 'ordre')
    
    paginator = Paginator(photos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Maisons disponibles selon les permissions
    if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'SUPER_ADMIN'):
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
    """Ajouter une nouvelle photo - ADAPTÉ"""
    if request.method == 'POST':
        form = PhotoMaisonForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                photo = form.save()
                messages.success(request, f'Photo ajoutée avec succès pour "{photo.maison.nom}".')
                return redirect('repavi_admin:photos_list')
            except Exception as e:
                messages.error(request, f'Erreur lors de l\'ajout : {str(e)}')
    else:
        form = PhotoMaisonForm(user=request.user)
    
    context = {'form': form, 'action': 'Ajouter'}
    return render(request, 'admin/photos/form.html', context)

@login_required
@gestionnaire_required
def admin_photo_edit(request, pk):
    """Modifier une photo - ADAPTÉ"""
    photo = get_object_or_404(PhotoMaison, pk=pk)
    
    if not photo.maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour modifier cette photo.")
        return redirect('repavi_admin:photos_list')
    
    if request.method == 'POST':
        form = PhotoMaisonForm(request.POST, request.FILES, instance=photo, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Photo modifiée avec succès.')
            return redirect('repavi_admin:photos_list')
    else:
        form = PhotoMaisonForm(instance=photo, user=request.user)
    
    context = {'form': form, 'action': 'Modifier', 'objet': photo}
    return render(request, 'admin/photos/form.html', context)

@login_required
@gestionnaire_required
def admin_photo_delete(request, pk):
    """Supprimer une photo - ADAPTÉ"""
    photo = get_object_or_404(PhotoMaison, pk=pk)
    
    if not photo.maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour supprimer cette photo.")
        return redirect('repavi_admin:photos_list')
    
    if request.method == 'POST':
        photo.delete()
        messages.success(request, f'Photo supprimée avec succès.')
        return redirect('repavi_admin:photos_list')
    
    context = {'objet': photo, 'type': 'photo'}
    return render(request, 'admin/confirm_delete.html', context)

# ======== GESTION DES RÉSERVATIONS ========

@login_required
@gestionnaire_required
def admin_reservations_list(request):
    """Liste des réservations - ADAPTÉ"""
    statut = request.GET.get('statut', '')
    search = request.GET.get('search', '')
    
    # Récupérer les réservations selon les permissions
    reservations = _get_fallback_reservations(request.user)
    
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
        'statuts': getattr(Reservation, 'STATUT_CHOICES', []),
        'can_change_status': hasattr(request.user, 'is_gestionnaire') and request.user.is_gestionnaire(),
    }
    
    return render(request, 'admin/reservations/list.html', context)

@login_required
@gestionnaire_required
def admin_reservation_create(request):
    """Créer une nouvelle réservation"""
    if request.method == 'POST':
        form = ReservationForm(request.POST, user=request.user)
        if form.is_valid():
            try:
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
def admin_reservation_edit(request, pk):
    """Modifier une réservation - ADAPTÉ"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    if not reservation.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour modifier cette réservation.")
        return redirect('repavi_admin:reservations_list')
    
    if request.method == 'POST':
        # Permettre seulement la modification du statut pour les gestionnaires
        nouveau_statut = request.POST.get('statut')
        if nouveau_statut and nouveau_statut in dict(getattr(Reservation, 'STATUT_CHOICES', [])):
            reservation.statut = nouveau_statut
            reservation.save()
            messages.success(request, f'Statut de la réservation mis à jour.')
            return redirect('repavi_admin:reservations_list')
    
    context = {
        'reservation': reservation,
        'statuts': getattr(Reservation, 'STATUT_CHOICES', []),
        'can_modify': reservation.can_be_managed_by(request.user),
    }
    
    return render(request, 'admin/reservations/edit.html', context)

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