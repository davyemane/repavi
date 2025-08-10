# apps/users/signals.py
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
import logging

# Import du middleware pour récupérer l'utilisateur actuel
from .middleware import get_current_user, get_current_request, get_client_ip

logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log des connexions"""
    try:
        # Import local pour éviter les imports circulaires
        from .models import ActionLog
        
        ActionLog.objects.create(
            utilisateur=user,
            action='login',
            model_name='User',
            object_id=str(user.pk),
            object_repr=f"Connexion: {user.username}",
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            url=request.get_full_path() if request else '',
            method='POST',
        )
    except Exception as e:
        logger.error(f"Erreur lors du logging de connexion: {e}")

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log des déconnexions"""
    if user:
        try:
            from .models import ActionLog
            
            ActionLog.objects.create(
                utilisateur=user,
                action='logout',
                model_name='User',
                object_id=str(user.pk),
                object_repr=f"Déconnexion: {user.username}",
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
                url=request.get_full_path() if request else '',
                method='GET',
            )
        except Exception as e:
            logger.error(f"Erreur lors du logging de déconnexion: {e}")

@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    """Log création/modification avec utilisateur"""
    # Import local pour éviter les imports circulaires
    from .models import ActionLog
    
    # Éviter la récursion infinie
    if sender == ActionLog:
        return
    
    # Ne pas logger pendant les migrations
    if kwargs.get('raw', False):
        return
    
    # Éviter les logs pendant les fixtures
    if kwargs.get('update_fields') == frozenset():
        return
    
    try:
        # Récupérer l'utilisateur actuel via le middleware
        current_user = get_current_user()
        current_request = get_current_request()
        
        # Informations de la requête si disponible
        ip_address = get_client_ip(current_request) if current_request else None
        user_agent = current_request.META.get('HTTP_USER_AGENT', '') if current_request else ''
        url = current_request.get_full_path() if current_request else ''
        method = current_request.method if current_request else ''
        
        with transaction.atomic():
            ActionLog.objects.create(
                utilisateur=current_user,
                action='create' if created else 'update',
                model_name=sender.__name__,
                object_id=str(instance.pk),
                object_repr=str(instance)[:200],
                ip_address=ip_address,
                user_agent=user_agent,
                url=url,
                method=method,
                details=f'{{"created": {str(created).lower()}, "model": "{sender._meta.verbose_name}"}}'
            )
    except Exception as e:
        logger.error(f"Erreur lors du logging de sauvegarde pour {sender.__name__}: {e}")

@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    """Log suppression avec utilisateur"""
    from .models import ActionLog
    
    # Éviter la récursion infinie
    if sender == ActionLog:
        return
    
    # Ne pas logger pendant les migrations
    if kwargs.get('raw', False):
        return
    
    try:
        current_user = get_current_user()
        current_request = get_current_request()
        
        # Informations de la requête si disponible
        ip_address = get_client_ip(current_request) if current_request else None
        user_agent = current_request.META.get('HTTP_USER_AGENT', '') if current_request else ''
        url = current_request.get_full_path() if current_request else ''
        method = current_request.method if current_request else ''
        
        ActionLog.objects.create(
            utilisateur=current_user,
            action='delete',
            model_name=sender.__name__,
            object_id=str(instance.pk),
            object_repr=str(instance)[:200],
            ip_address=ip_address,
            user_agent=user_agent,
            url=url,
            method=method,
            details=f'{{"model": "{sender._meta.verbose_name}"}}'
        )
    except Exception as e:
        logger.error(f"Erreur lors du logging de suppression pour {sender.__name__}: {e}")

# ==========================================
# Décorateur pour actions manuelles
# ==========================================
def log_action(action, model_name, object_repr, object_id=None):
    """Décorateur pour logger des actions spécifiques"""
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            result = func(request, *args, **kwargs)
            
            # Logger l'action si succès
            try:
                if hasattr(request, 'user') and request.user.is_authenticated:
                    from .models import ActionLog
                    
                    ActionLog.objects.create(
                        utilisateur=request.user,
                        action=action,
                        model_name=model_name,
                        object_id=str(object_id) if object_id else '',
                        object_repr=object_repr,
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        url=request.get_full_path(),
                        method=request.method,
                    )
            except Exception as e:
                logger.error(f"Erreur lors du logging manuel d'action: {e}")
            
            return result
        return wrapper
    return decorator

# apps/users/signals.py
from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session

def on_user_logged_in(sender, user, request, **kwargs):
    # Supprimer autres sessions
    Session.objects.filter(session_data__contains=f'"_auth_user_id":"{user.pk}"').exclude(
        session_key=request.session.session_key
    ).delete()
    
    user.session_key = request.session.session_key
    user.save()

user_logged_in.connect(on_user_logged_in)

def log_model_change(sender, instance, created, **kwargs):
    # Récupérer l'utilisateur depuis le middleware ou request
    user = getattr(instance, '_current_user', None)
    
    # Vérifier que c'est un vrai utilisateur
    if not user or not user.is_authenticated or user.is_anonymous:
        return  # Ignorer le logging
    
    try:
        from .models import ActionLog
        ActionLog.objects.create(
            utilisateur=user,
            action='create' if created else 'update',
            model_name=sender.__name__,
            object_id=str(instance.pk),
            # ... autres champs
        )
    except Exception as e:
        # Logging silencieux en cas d'erreur
        pass