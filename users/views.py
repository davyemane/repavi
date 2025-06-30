# users/views.py - Version adaptée avec nouveaux rôles et services
import uuid
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction

from reservations.views import client_required
from services.reservation_service import ReservationService
from services.statistics_service import StatisticsService
from .models import User, TokenVerificationEmail, PasswordResetToken, ProfilGestionnaire, ProfilClient
from .forms import (
    CustomLoginForm, SimpleRegistrationForm, ProfileForm,
    CustomPasswordChangeForm, PasswordResetRequestForm, PasswordResetForm,
    ProfilGestionnaireForm, ProfilClientForm, ChangeUserRoleForm
)

from django.db.models import Sum  # Si pas déjà importé

from django.db.models import Q  # Ajoutez cette ligne si elle n'existe pas
from home.models import Maison  # Import du modèle Maison
from reservations.models import Reservation  # Import du modèle Reservation

# Si vous avez un service de réservation, importez-le aussi
try:
    from services.reservation_service import ReservationService
except ImportError:
    # Fallback si le service n'existe pas
    class ReservationService:
        @staticmethod
        def get_reservations_for_user(user):
            if hasattr(user, 'is_client') and user.is_client():
                return Reservation.objects.filter(client=user)
            elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
                return Reservation.objects.filter(maison__gestionnaire=user)
            else:
                return Reservation.objects.none()


def login_view(request):
    """Vue de connexion - ADAPTÉE AVEC REDIRECTIONS PAR RÔLE"""
    if request.user.is_authenticated:
        return redirect('home:index')
    
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Gérer "Se souvenir de moi"
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)
            
            # Mettre à jour les infos de connexion
            user.date_derniere_connexion_complete = timezone.now()
            if hasattr(request, 'META'):
                user.ip_derniere_connexion = request.META.get('REMOTE_ADDR')
            user.save(update_fields=['date_derniere_connexion_complete', 'ip_derniere_connexion'])
            
            messages.success(request, f'Bon retour, {user.first_name}!')
            
            # Redirection après connexion selon le NOUVEAU SYSTÈME DE RÔLES
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            # Redirection selon le nouveau rôle
            if user.is_super_admin() or user.is_superuser:
                return redirect('repavi_admin:dashboard')
            elif user.is_gestionnaire():
                return redirect('users:dashboard_gestionnaire')
            elif user.is_client():
                return redirect('users:dashboard_client')
            else:
                return redirect('home:index')
        else:
            messages.error(request, 'Email ou mot de passe incorrect.')
    else:
        form = CustomLoginForm()
    
    return render(request, 'users/login.html', {'form': form})


def register_view(request):
    """Vue d'inscription simplifiée"""
    if request.user.is_authenticated:
        return redirect('home:index')
    
    if request.method == 'POST':
        form = SimpleRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    
                    # Connecter automatiquement l'utilisateur
                    login(request, user)
                    
                    # Message selon le rôle choisi
                    role_messages = {
                        'CLIENT': 'Bienvenue ! Votre compte client a été créé avec succès.',
                        'GESTIONNAIRE': 'Bienvenue ! Votre compte gestionnaire a été créé. Vous pouvez maintenant ajouter vos maisons.'
                    }
                    
                    messages.success(request, role_messages.get(user.role, "Votre compte a été créé avec succès !"))
                    
                    # Redirection selon le rôle
                    if user.role == 'GESTIONNAIRE':
                        return redirect('maisons:mes_maisons')  # Vers la gestion des maisons
                    else:
                        return redirect('home:index')  # Vers l'accueil pour les clients
                        
            except Exception as e:
                messages.error(request, 'Une erreur est survenue lors de la création de votre compte. Veuillez réessayer.')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = SimpleRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})
@login_required
def dashboard_view(request):
    """Dashboard principal selon le NOUVEAU type d'utilisateur"""
    if request.user.is_gestionnaire():
        return dashboard_gestionnaire_view(request)
    elif request.user.is_client():
        return dashboard_client_view(request)
    elif request.user.is_super_admin():
        return redirect('repavi_admin:dashboard')
    else:
        return redirect('home:index')


@login_required
def dashboard_gestionnaire_view(request):
    """Dashboard pour les gestionnaires - ADAPTÉ AVEC SERVICES"""
    if not request.user.is_gestionnaire():
        messages.error(request, "Accès réservé aux gestionnaires.")
        return redirect('home:index')
    
    # Utiliser le service de statistiques
    stats = StatisticsService.get_dashboard_stats(request.user)
    
    # Réservations récentes
    reservations_recentes = ReservationService.get_reservations_for_user(request.user)[:5]
    
    # Maisons du gestionnaire
    from home.models import Maison
    maisons = Maison.objects.filter(gestionnaire=request.user).prefetch_related('photos')
    
    # Réservations en attente nécessitant une action
    reservations_en_attente = ReservationService.get_reservations_for_user(request.user).filter(
        statut='en_attente'
    )[:3]
    
    # Vérifier si le profil gestionnaire est complet
    try:
        profil_gestionnaire = request.user.profil_gestionnaire
        profil_complet = bool(profil_gestionnaire.piece_identite and profil_gestionnaire.justificatif_domicile)
    except ProfilGestionnaire.DoesNotExist:
        ProfilGestionnaire.objects.create(user=request.user)
        profil_complet = False
    
    context = {
        'stats': stats,
        'maisons': maisons[:3],  # Les 3 dernières
        'reservations_recentes': reservations_recentes,
        'reservations_en_attente': reservations_en_attente,
        'profil_complet': profil_complet,
        'user_role': request.user.role,
    }
    
    return render(request, 'users/dashboard_gestionnaire.html', context)

@login_required
@client_required
def mes_reservations_client(request):
    """Vue simplifiée des réservations pour les clients"""
    # Récupérer uniquement les réservations du client connecté
    reservations = Reservation.objects.filter(
        client=request.user
    ).select_related('maison', 'client').prefetch_related('maison__photos').order_by('-date_creation')
    
    # Filtrage simple
    statut_filter = request.GET.get('statut', '')
    search = request.GET.get('search', '')
    
    if statut_filter:
        reservations = reservations.filter(statut=statut_filter)
    
    if search:
        reservations = reservations.filter(
            Q(numero__icontains=search) |
            Q(maison__nom__icontains=search)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(reservations, 8)  # 8 réservations par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiques simples pour le client
    stats = {
        'total': reservations.count(),
        'en_cours': reservations.filter(statut__in=['en_attente', 'confirmee']).count(),
        'terminees': reservations.filter(statut='terminee').count(),
        'annulees': reservations.filter(statut='annulee').count(),
    }
    
    # Calculer le montant total dépensé (réservations confirmées et terminées)
    montant_total = reservations.filter(
        statut__in=['confirmee', 'terminee']
    ).aggregate(total=Sum('prix_total'))['total'] or 0
    
    # Prochaine réservation
    prochaine_reservation = reservations.filter(
        statut='confirmee',
        date_debut__gte=timezone.now().date()
    ).order_by('date_debut').first()
    
    # Choix de statut pour le filtre
    statut_choices = [
        ('', 'Toutes'),
        ('en_attente', 'En attente'),
        ('confirmee', 'Confirmée'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'montant_total': montant_total,
        'prochaine_reservation': prochaine_reservation,
        'statut_filter': statut_filter,
        'search': search,
        'statut_choices': statut_choices,
    }
    
    return render(request, 'users/mes_reservations_client.html', context)

@login_required
def dashboard_client_view(request):
    """Dashboard pour les clients - ADAPTÉ AVEC SERVICES"""
    if not request.user.is_client():
        messages.error(request, "Accès réservé aux clients.")
        return redirect('home:index')
    
    # Réservations du client
    reservations = ReservationService.get_reservations_for_user(request.user)
    reservations_actives = reservations.filter(statut__in=['en_attente', 'confirmee'])
    reservations_passees = reservations.filter(statut='terminee')
    
    # Maisons recommandées - prendre quelques maisons populaires ou récentes
    maisons_recommandees = Maison.objects.filter(
        disponible=True,
        statut_occupation='libre'
    ).select_related('ville', 'categorie').prefetch_related('photos').order_by('-date_creation')[:3]
    
    # Si pas assez de maisons récentes, prendre les mieux notées
    if maisons_recommandees.count() < 3:
        maisons_recommandees = Maison.objects.filter(
            disponible=True,
            statut_occupation='libre'
        ).select_related('ville', 'categorie').prefetch_related('photos').order_by('?')[:3]
    
    # Vérifier si le profil client est complet
    try:
        profil_client = request.user.profil_client
        profil_complet = bool(profil_client.piece_identite)
    except ProfilClient.DoesNotExist:
        ProfilClient.objects.create(user=request.user)
        profil_complet = False
    
    context = {
        'reservations_actives': reservations_actives,
        'reservations_passees': reservations_passees[:3],  # Les 3 dernières
        'nombre_sejours': reservations_passees.count(),
        'profil_complet': profil_complet,
        'user_role': request.user.role,
        'maisons_recommandees': maisons_recommandees,  # Ajout des maisons recommandées
    }
    
    return render(request, 'users/dashboard_client.html', context)
@login_required
def profile_view(request):
    """Vue du profil utilisateur - ADAPTÉE AVEC PROFILS ÉTENDUS"""
    # Formulaire principal
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        
        # Formulaires étendus selon le rôle
        profil_form = None
        if request.user.is_gestionnaire():
            try:
                profil_gestionnaire = request.user.profil_gestionnaire
            except ProfilGestionnaire.DoesNotExist:
                profil_gestionnaire = ProfilGestionnaire.objects.create(user=request.user)
            
            profil_form = ProfilGestionnaireForm(request.POST, request.FILES, instance=profil_gestionnaire)
        
        elif request.user.is_client():
            try:
                profil_client = request.user.profil_client
            except ProfilClient.DoesNotExist:
                profil_client = ProfilClient.objects.create(user=request.user)
            
            profil_form = ProfilClientForm(request.POST, request.FILES, instance=profil_client)
        
        # Validation et sauvegarde
        if form.is_valid() and (profil_form is None or profil_form.is_valid()):
            with transaction.atomic():
                form.save()
                if profil_form:
                    profil_form.save()
            
            messages.success(request, 'Votre profil a été mis à jour avec succès.')
            return redirect('users:profile')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    
    else:
        form = ProfileForm(instance=request.user)
        profil_form = None
        
        if request.user.is_gestionnaire():
            try:
                profil_gestionnaire = request.user.profil_gestionnaire
            except ProfilGestionnaire.DoesNotExist:
                profil_gestionnaire = ProfilGestionnaire.objects.create(user=request.user)
            profil_form = ProfilGestionnaireForm(instance=profil_gestionnaire)
        
        elif request.user.is_client():
            try:
                profil_client = request.user.profil_client
            except ProfilClient.DoesNotExist:
                profil_client = ProfilClient.objects.create(user=request.user)
            profil_form = ProfilClientForm(instance=profil_client)
    
    context = {
        'form': form,
        'profil_form': profil_form,
        'user_role': request.user.role,
    }
    
    return render(request, 'users/profile.html', context)



@login_required
def mes_maisons_view(request):
    """Vue des maisons du gestionnaire - NOUVELLE"""
    if not request.user.is_gestionnaire():
        messages.error(request, "Cette page est réservée aux gestionnaires.")
        return redirect('users:dashboard')
    
    from home.models import Maison
    from services.maison_service import MaisonService
    
    maisons = MaisonService.get_maisons_for_user(request.user)
    
    # Filtres
    disponible = request.GET.get('disponible', '')
    if disponible:
        maisons = maisons.filter(disponible=disponible == 'True')
    
    from django.core.paginator import Paginator
    paginator = Paginator(maisons, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'disponible_actuel': disponible,
    }
    
    return render(request, 'users/mes_maisons.html', context)


# ======== VUES EXISTANTES ADAPTÉES ========

def send_email_verification(user):
    """Envoyer un email de vérification - GARDÉ IDENTIQUE"""
    token = str(uuid.uuid4())
    expires_at = timezone.now() + timedelta(hours=24)
    
    TokenVerificationEmail.objects.create(
        user=user,
        token=token,
        expires_at=expires_at
    )
    
    verification_url = f"{settings.SITE_URL}/users/verify-email/{token}/"
    
    subject = "Vérifiez votre email - RepAvi"
    message = f"""
    Bonjour {user.first_name},
    
    Merci de vous être inscrit sur RepAvi en tant que {user.get_role_display()}!
    
    Pour activer votre compte, cliquez sur le lien ci-dessous :
    {verification_url}
    
    Ce lien expire dans 24 heures.
    
    Si vous n'avez pas créé de compte, ignorez cet email.
    
    L'équipe RepAvi
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def verify_email(request, token):
    """Vérifier l'email avec le token - GARDÉ IDENTIQUE"""
    try:
        verification = get_object_or_404(TokenVerificationEmail, token=token)
        
        if verification.is_used:
            messages.error(request, 'Ce lien de vérification a déjà été utilisé.')
            return redirect('users:login')
        
        if verification.is_expired():
            messages.error(request, 'Ce lien de vérification a expiré.')
            return redirect('users:resend_verification')
        
        user = verification.user
        user.email_verifie = True
        user.is_active = True
        user.save()
        
        verification.is_used = True
        verification.save()
        
        role_message = {
            'CLIENT': 'Votre compte client est maintenant activé!',
            'GESTIONNAIRE': 'Votre compte gestionnaire est activé! Vous pouvez commencer à ajouter vos maisons.',
            'SUPER_ADMIN': 'Votre compte administrateur est activé!'
        }
        
        messages.success(request, 
            f'{role_message.get(user.role, "Votre email a été vérifié avec succès!")} '
            'Vous pouvez maintenant vous connecter.')
        return redirect('users:login')
        
    except Exception:
        messages.error(request, 'Lien de vérification invalide.')
        return redirect('users:login')


@login_required
def logout_view(request):
    """Vue de déconnexion - GARDÉE IDENTIQUE"""
    logout(request)
    messages.info(request, 'Vous avez été déconnecté avec succès.')
    return redirect('home:index')


@login_required
def change_password_view(request):
    """Vue de changement de mot de passe - GARDÉE IDENTIQUE"""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Votre mot de passe a été modifié avec succès.')
            return redirect('users:profile')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'users/change_password.html', {'form': form})


# ======== VUES POUR SUPER ADMIN ========

@login_required
def admin_users_list(request):
    """Liste des utilisateurs - SUPER ADMIN SEULEMENT"""
    if not request.user.is_super_admin():
        messages.error(request, "Accès réservé aux super administrateurs.")
        return redirect('users:dashboard')
    
    role_filter = request.GET.get('role', '')
    search = request.GET.get('search', '')
    
    users = User.objects.all()
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    users = users.order_by('-date_joined')
    
    from django.core.paginator import Paginator
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'role_filter': role_filter,
        'search': search,
        'roles': User.ROLE_CHOICES,
    }
    
    return render(request, 'users/admin_users_list.html', context)


@login_required
def change_user_role_view(request, user_id):
    """Changer le rôle d'un utilisateur - SUPER ADMIN SEULEMENT"""
    if not request.user.is_super_admin():
        messages.error(request, "Accès réservé aux super administrateurs.")
        return redirect('users:dashboard')
    
    user_to_modify = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = ChangeUserRoleForm(request.POST, instance=user_to_modify)
        if form.is_valid():
            old_role = user_to_modify.role
            new_role = form.cleaned_data['role']
            
            if old_role != new_role:
                with transaction.atomic():
                    form.save()
                    
                    # Créer/supprimer les profils étendus selon le nouveau rôle
                    if new_role == 'GESTIONNAIRE' and old_role != 'GESTIONNAIRE':
                        ProfilGestionnaire.objects.get_or_create(user=user_to_modify)
                    elif new_role == 'CLIENT' and old_role != 'CLIENT':
                        ProfilClient.objects.get_or_create(user=user_to_modify)
                
                messages.success(request, 
                    f'Rôle de {user_to_modify.nom_complet} changé de {old_role} à {new_role}.')
            
            return redirect('users:admin_users_list')
    else:
        form = ChangeUserRoleForm(instance=user_to_modify)
    
    context = {
        'form': form,
        'user_to_modify': user_to_modify,
    }
    
    return render(request, 'users/change_user_role.html', context)


# ======== API ENDPOINTS POUR AJAX ========

@login_required
@require_http_methods(["POST"])
def check_password_ajax(request):
    """Vérifier le mot de passe actuel via AJAX - GARDÉ IDENTIQUE"""
    password = request.POST.get('password')
    user = authenticate(username=request.user.username, password=password)
    
    if user is not None and user == request.user:
        return JsonResponse({'valid': True})
    else:
        return JsonResponse({'valid': False, 'error': 'Mot de passe incorrect'})


@login_required
@require_http_methods(["POST"])
def toggle_notification_ajax(request):
    """Activer/désactiver une notification via AJAX - GARDÉ IDENTIQUE"""
    notification_type = request.POST.get('type')
    enabled = request.POST.get('enabled') == 'true'
    
    if notification_type in ['notifications_email', 'notifications_sms', 'newsletter']:
        setattr(request.user, notification_type, enabled)
        request.user.save(update_fields=[notification_type])
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Type de notification invalide'})


def user_exists_ajax(request):
    """Vérifier si un utilisateur existe déjà via AJAX - GARDÉ IDENTIQUE"""
    email = request.GET.get('email')
    if email:
        exists = User.objects.filter(email=email).exists()
        return JsonResponse({'exists': exists})
    return JsonResponse({'exists': False})


# Autres vues gardées identiques (password reset, etc.)
def password_reset_request_view(request):
    """Vue de demande de réinitialisation de mot de passe - GARDÉE IDENTIQUE"""
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                send_password_reset_email(user)
                messages.success(request, 
                    'Un email de réinitialisation a été envoyé à votre adresse email.')
                return redirect('users:login')
            except User.DoesNotExist:
                messages.error(request, 'Aucun compte associé à cet email.')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'users/password_reset_request.html', {'form': form})


def send_password_reset_email(user):
    """Envoyer un email de réinitialisation de mot de passe - GARDÉE IDENTIQUE"""
    token = str(uuid.uuid4())
    expires_at = timezone.now() + timedelta(hours=1)
    
    PasswordResetToken.objects.create(
        user=user,
        token=token,
        expires_at=expires_at
    )
    
    reset_url = f"{settings.SITE_URL}/users/password-reset/{token}/"
    
    subject = "Réinitialisation de votre mot de passe - RepAvi"
    message = f"""
    Bonjour {user.first_name},
    
    Vous avez demandé la réinitialisation de votre mot de passe sur RepAvi.
    
    Pour créer un nouveau mot de passe, cliquez sur le lien ci-dessous :
    {reset_url}
    
    Ce lien expire dans 1 heure.
    
    Si vous n'avez pas fait cette demande, ignorez cet email.
    
    L'équipe RepAvi
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def password_reset_view(request, token):
    """Vue de réinitialisation de mot de passe - GARDÉE IDENTIQUE"""
    try:
        reset_token = get_object_or_404(PasswordResetToken, token=token)
        
        if reset_token.is_used:
            messages.error(request, 'Ce lien de réinitialisation a déjà été utilisé.')
            return redirect('users:password_reset_request')
        
        if reset_token.is_expired():
            messages.error(request, 'Ce lien de réinitialisation a expiré.')
            return redirect('users:password_reset_request')
        
        if request.method == 'POST':
            form = PasswordResetForm(request.POST)
            if form.is_valid():
                user = reset_token.user
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                
                reset_token.is_used = True
                reset_token.save()
                
                messages.success(request, 'Votre mot de passe a été réinitialisé avec succès.')
                return redirect('users:login')
        else:
            form = PasswordResetForm()
        
        return render(request, 'users/password_reset.html', {'form': form, 'token': token})
        
    except Exception:
        messages.error(request, 'Lien de réinitialisation invalide.')
        return redirect('users:password_reset_request')


@login_required
def resend_verification_view(request):
    """Renvoyer l'email de vérification - GARDÉE IDENTIQUE"""
    if request.user.email_verifie:
        messages.info(request, 'Votre email est déjà vérifié.')
        return redirect('users:profile')
    
    if request.method == 'POST':
        TokenVerificationEmail.objects.filter(
            user=request.user,
            is_used=False
        ).delete()
        
        send_email_verification(request.user)
        messages.success(request, 'Un nouvel email de vérification a été envoyé.')
        return redirect('users:profile')
    
    return render(request, 'users/resend_verification.html')


@login_required
@require_http_methods(["POST"])
def delete_account_view(request):
    """Supprimer le compte utilisateur - GARDÉE IDENTIQUE"""
    if request.method == 'POST':
        password = request.POST.get('password')
        user = authenticate(username=request.user.username, password=password)
        
        if user is not None and user == request.user:
            user.delete()
            logout(request)
            messages.success(request, 'Votre compte a été supprimé avec succès.')
            return redirect('home:index')
        else:
            messages.error(request, 'Mot de passe incorrect.')
    
    return redirect('users:profile')


@login_required
def account_settings_view(request):
    """Paramètres du compte - GARDÉE IDENTIQUE"""
    return render(request, 'users/account_settings.html')