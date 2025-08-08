from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.users.middleware import get_current_user
from .models import ActionLog, User
from ipware import get_client_ip


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log des connexions"""
    ActionLog.objects.create(
        utilisateur=user,
        action='login',
        model_name='User',
        object_id=str(user.pk),
        object_repr=f"Connexion: {user.username}",
        ip_address=get_client_ip(request) if request else None,
        user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
        url=request.get_full_path() if request else '',
        method='POST',
    )

@receiver(user_logged_out) 
def log_user_logout(sender, request, user, **kwargs):
    """Log des déconnexions"""
    if user:
        ActionLog.objects.create(
            utilisateur=user,
            action='logout',
            model_name='User', 
            object_id=str(user.pk),
            object_repr=f"Déconnexion: {user.username}",
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            url=request.get_full_path() if request else '',
            method='GET',
        )

@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    """Log création/modification avec utilisateur"""
    if sender == ActionLog:
        return
    
    # Récupérer l'utilisateur actuel
    current_user = get_current_user()
    
    ActionLog.objects.create(
        utilisateur=current_user,
        action='create' if created else 'update',
        model_name=sender.__name__,
        object_id=str(instance.pk),
        object_repr=str(instance)[:200],  # Limiter la taille
        details=f'{{"created": {str(created).lower()}, "model": "{sender._meta.verbose_name}"}}'
    )

@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    """Log suppression avec utilisateur"""
    if sender == ActionLog:
        return
    
    current_user = get_current_user()
    
    ActionLog.objects.create(
        utilisateur=current_user,
        action='delete',
        model_name=sender.__name__,
        object_id=str(instance.pk),
        object_repr=str(instance)[:200],
        details=f'{{"model": "{sender._meta.verbose_name}"}}'
    )

def get_client_ip(request):
    """Helper IP"""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

# ==========================================
# Décorateur pour actions manuelles
# ==========================================
def log_action(action, model_name, object_repr, object_id=None):
    """Décorateur pour logger des actions spécifiques"""
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            result = func(request, *args, **kwargs)
            
            # Logger l'action si succès
            if hasattr(request, 'user') and request.user.is_authenticated:
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
            
            return result
        return wrapper
    return decorator