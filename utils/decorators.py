# utils/decorators.py
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages


def role_required(allowed_roles):
    """
    Décorateur pour vérifier que l'utilisateur a un des rôles autorisés
    Usage: @role_required(['GESTIONNAIRE', 'SUPER_ADMIN'])
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            messages.error(request, "Accès non autorisé pour votre rôle.")
            raise PermissionDenied("Accès non autorisé pour votre rôle")
        return _wrapped_view
    return decorator


def gestionnaire_required(view_func):
    """
    Décorateur pour les vues nécessitant les droits de gestionnaire
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.has_gestionnaire_permissions():
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "Accès gestionnaire requis.")
        return redirect('home:index')
    return _wrapped_view


def client_required(view_func):
    """
    Décorateur pour les vues nécessitant d'être un client
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_client():
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "Accès client requis.")
        return redirect('home:index')
    return _wrapped_view


def super_admin_required(view_func):
    """
    Décorateur pour les vues nécessitant les droits de super admin
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_super_admin() or request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        messages.error(request, "Accès super admin requis.")
        return redirect('home:index')
    return _wrapped_view


def receptionniste_required(view_func):
    """
    Décorateur pour les vues nécessitant les droits de réceptionniste (ou supérieur)
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_receptionniste():
            return view_func(request, *args, **kwargs)

        messages.error(request, "Accès réceptionniste requis.")
        return redirect('home:index')
    return _wrapped_view


# Mixins pour Class-Based Views
class RoleRequiredMixin:
    """
    Mixin pour vérifier les rôles dans les Class-Based Views
    """
    required_roles = []
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        
        if request.user.role not in self.required_roles:
            messages.error(request, "Accès non autorisé pour votre rôle.")
            raise PermissionDenied("Accès non autorisé pour votre rôle")
        
        return super().dispatch(request, *args, **kwargs)


class GestionnaireRequiredMixin:
    """
    Mixin pour les vues nécessitant les droits de gestionnaire
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        
        if not request.user.has_gestionnaire_permissions():
            messages.error(request, "Accès gestionnaire requis.")
            raise PermissionDenied("Accès gestionnaire requis")
        
        return super().dispatch(request, *args, **kwargs)


class ClientRequiredMixin:
    """
    Mixin pour les vues nécessitant d'être un client
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        
        if not request.user.is_client():
            messages.error(request, "Accès client requis.")
            return redirect('home:index')
        
        return super().dispatch(request, *args, **kwargs)


class SuperAdminRequiredMixin:
    """
    Mixin pour les vues nécessitant les droits de super admin
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')

        if not (request.user.is_super_admin() or request.user.is_superuser):
            messages.error(request, "Accès super admin requis.")
            raise PermissionDenied("Accès super admin requis")

        return super().dispatch(request, *args, **kwargs)


class ReceptionnisteRequiredMixin:
    """
    Mixin pour les vues nécessitant les droits de réceptionniste (ou supérieur)
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')

        if not request.user.is_receptionniste():
            messages.error(request, "Accès réceptionniste requis.")
            raise PermissionDenied("Accès réceptionniste requis")

        return super().dispatch(request, *args, **kwargs)


# Décorateur pour vérifier qu'un utilisateur peut gérer un objet spécifique
def can_manage_object(get_object_func):
    """
    Décorateur pour vérifier qu'un utilisateur peut gérer un objet spécifique
    Usage: @can_manage_object(lambda request, pk: get_object_or_404(Maison, pk=pk))
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            obj = get_object_func(request, *args, **kwargs)
            
            if hasattr(obj, 'can_be_managed_by') and obj.can_be_managed_by(request.user):
                return view_func(request, *args, **kwargs)
            
            messages.error(request, "Vous n'avez pas les droits pour gérer cet objet.")
            raise PermissionDenied("Accès non autorisé pour cet objet")
        return _wrapped_view
    return decorator