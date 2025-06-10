# users/views.py
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

from .models import User, TokenVerificationEmail, PasswordResetToken
from .forms import (
    CustomLoginForm, CustomRegistrationForm, ProfileForm,
    CustomPasswordChangeForm, PasswordResetRequestForm, PasswordResetForm
)


def login_view(request):
    """Vue de connexion"""
    if request.user.is_authenticated:
        return redirect('home:index')
    
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Gérer "Se souvenir de moi"
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)  # Session expire à la fermeture du navigateur
            
            # Mettre à jour les infos de connexion
            user.date_derniere_connexion_complete = timezone.now()
            if hasattr(request, 'META'):
                user.ip_derniere_connexion = request.META.get('REMOTE_ADDR')
            user.save(update_fields=['date_derniere_connexion_complete', 'ip_derniere_connexion'])
            
            messages.success(request, f'Bon retour, {user.first_name}!')
            
            # Redirection après connexion
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            # Redirection selon le type d'utilisateur
            if user.est_admin:
                return redirect('repavi_admin:dashboard')
            elif user.est_proprietaire:
                return redirect('users:dashboard_proprietaire')
            else:
                return redirect('home:index')
        else:
            messages.error(request, 'Email ou mot de passe incorrect.')
    else:
        form = CustomLoginForm()
    
    return render(request, 'users/login.html', {'form': form})


def register_view(request):
    """Vue d'inscription"""
    if request.user.is_authenticated:
        return redirect('home:index')
    
    if request.method == 'POST':
        form = CustomRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    
                    # Envoyer l'email de vérification
                    send_email_verification(user)
                    
                    messages.success(request, 
                        'Votre compte a été créé avec succès! '
                        'Veuillez vérifier votre email pour activer votre compte.')
                    
                    return redirect('users:login')
            except Exception as e:
                messages.error(request, 'Une erreur est survenue lors de la création de votre compte.')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = CustomRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})


def send_email_verification(user):
    """Envoyer un email de vérification"""
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
    
    Merci de vous être inscrit sur RepAvi !
    
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
    """Vérifier l'email avec le token"""
    try:
        verification = get_object_or_404(TokenVerificationEmail, token=token)
        
        if verification.is_used:
            messages.error(request, 'Ce lien de vérification a déjà été utilisé.')
            return redirect('users:login')
        
        if verification.is_expired():
            messages.error(request, 'Ce lien de vérification a expiré.')
            return redirect('users:resend_verification')
        
        # Activer le compte
        user = verification.user
        user.email_verifie = True
        user.is_active = True
        user.save()
        
        verification.is_used = True
        verification.save()
        
        messages.success(request, 'Votre email a été vérifié avec succès! Vous pouvez maintenant vous connecter.')
        return redirect('users:login')
        
    except Exception:
        messages.error(request, 'Lien de vérification invalide.')
        return redirect('users:login')


@login_required
def logout_view(request):
    """Vue de déconnexion"""
    logout(request)
    messages.info(request, 'Vous avez été déconnecté avec succès.')
    return redirect('home:index')


@login_required
def profile_view(request):
    """Vue du profil utilisateur"""
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre profil a été mis à jour avec succès.')
            return redirect('users:profile')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = ProfileForm(instance=request.user)
    
    return render(request, 'users/profile.html', {'form': form})


@login_required
def change_password_view(request):
    """Vue de changement de mot de passe"""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important pour ne pas déconnecter l'utilisateur
            messages.success(request, 'Votre mot de passe a été modifié avec succès.')
            return redirect('users:profile')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'users/change_password.html', {'form': form})


def password_reset_request_view(request):
    """Vue de demande de réinitialisation de mot de passe"""
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
    """Envoyer un email de réinitialisation de mot de passe"""
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
    """Vue de réinitialisation de mot de passe"""
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
def dashboard_view(request):
    """Dashboard principal selon le type d'utilisateur"""
    if request.user.est_proprietaire:
        return dashboard_proprietaire_view(request)
    elif request.user.est_locataire:
        return dashboard_locataire_view(request)
    else:
        return redirect('home:index')


@login_required
def dashboard_proprietaire_view(request):
    """Dashboard pour les propriétaires"""
    from home.models import Maison, Reservation
    
    # Récupérer les maisons du propriétaire
    maisons = Maison.objects.filter(proprietaire=request.user)
    
    # Réservations en cours
    reservations_en_cours = Reservation.objects.filter(
        maison__proprietaire=request.user,
        statut__in=['en_attente', 'confirmee']
    )
    
    # Statistiques calculées
    maisons_disponibles = maisons.filter(disponible=True).count()
    reservations_attente = reservations_en_cours.filter(statut='en_attente').count()
    
    context = {
        'maisons': maisons,
        'nombre_maisons': maisons.count(),
        'maisons_disponibles': maisons_disponibles,
        'reservations_en_cours': reservations_en_cours,
        'nombre_reservations': reservations_en_cours.count(),
        'reservations_attente': reservations_attente,
        'revenus_mois': sum(r.prix_total for r in reservations_en_cours),
    }
    
    return render(request, 'users/dashboard_proprietaire.html', context)

@login_required
def dashboard_locataire_view(request):
    """Dashboard pour les locataires"""
    from home.models import Reservation
    
    # Réservations du locataire
    reservations = Reservation.objects.filter(locataire=request.user)
    reservations_actives = reservations.filter(statut__in=['en_attente', 'confirmee'])
    
    context = {
        'reservations': reservations[:5],  # Les 5 dernières
        'reservations_actives': reservations_actives,
        'nombre_sejours': reservations.filter(statut='terminee').count(),
    }
    
    return render(request, 'users/dashboard_locataire.html', context)


@login_required
def resend_verification_view(request):
    """Renvoyer l'email de vérification"""
    if request.user.email_verifie:
        messages.info(request, 'Votre email est déjà vérifié.')
        return redirect('users:profile')
    
    if request.method == 'POST':
        # Supprimer les anciens tokens non utilisés
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
    """Supprimer le compte utilisateur"""
    if request.method == 'POST':
        password = request.POST.get('password')
        user = authenticate(username=request.user.username, password=password)
        
        if user is not None and user == request.user:
            # Supprimer le compte
            user.delete()
            logout(request)
            messages.success(request, 'Votre compte a été supprimé avec succès.')
            return redirect('home:index')
        else:
            messages.error(request, 'Mot de passe incorrect.')
    
    return redirect('users:profile')


@login_required
def account_settings_view(request):
    """Paramètres du compte"""
    return render(request, 'users/account_settings.html')


# API Views pour AJAX
@login_required
@require_http_methods(["POST"])
def check_password_ajax(request):
    """Vérifier le mot de passe actuel via AJAX"""
    password = request.POST.get('password')
    user = authenticate(username=request.user.email, password=password)
    
    if user is not None and user == request.user:
        return JsonResponse({'valid': True})
    else:
        return JsonResponse({'valid': False, 'error': 'Mot de passe incorrect'})


@login_required
@require_http_methods(["POST"])
def toggle_notification_ajax(request):
    """Activer/désactiver une notification via AJAX"""
    notification_type = request.POST.get('type')
    enabled = request.POST.get('enabled') == 'true'
    
    if notification_type in ['notifications_email', 'notifications_sms', 'newsletter']:
        setattr(request.user, notification_type, enabled)
        request.user.save(update_fields=[notification_type])
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Type de notification invalide'})


def user_exists_ajax(request):
    """Vérifier si un utilisateur existe déjà via AJAX"""
    email = request.GET.get('email')
    if email:
        exists = User.objects.filter(email=email).exists()
        return JsonResponse({'exists': exists})
    return JsonResponse({'exists': False})