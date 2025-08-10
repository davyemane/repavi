# apps/users/middleware.py
from django.contrib import messages
import threading
from django.utils.deprecation import MiddlewareMixin

# Thread local pour stocker l'utilisateur actuel
_thread_locals = threading.local()

def get_current_user():
    """Récupère l'utilisateur actuel depuis thread local"""
    return getattr(_thread_locals, 'user', None)

def set_current_user(user):
    """Définit l'utilisateur actuel dans thread local"""
    _thread_locals.user = user

def get_current_request():
    """Récupère la requête actuelle depuis thread local"""
    return getattr(_thread_locals, 'request', None)

def set_current_request(request):
    """Définit la requête actuelle dans thread local"""
    _thread_locals.request = request

class CurrentUserMiddleware(MiddlewareMixin):
    """Middleware pour capturer l'utilisateur et la requête dans les signaux"""
    
    def process_request(self, request):
        # Stocker l'utilisateur et la requête dans thread local
        if hasattr(request, 'user') and request.user.is_authenticated:
            set_current_user(request.user)
        else:
            set_current_user(None)
        
        set_current_request(request)
        return None
    
    def process_response(self, request, response):
        # Nettoyer le thread local
        set_current_user(None)
        set_current_request(None)
        return response
    
    def process_exception(self, request, exception):
        # Nettoyer en cas d'exception
        set_current_user(None)
        set_current_request(None)
        return None

def get_client_ip(request):
    """Helper pour récupérer l'IP du client"""
    if not request:
        return None
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

from django.contrib.auth import logout
from django.contrib.sessions.models import Session

class SingleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            stored_session_key = getattr(request.user, 'session_key', None)
            current_session_key = request.session.session_key
            
            if stored_session_key and stored_session_key != current_session_key:
                Session.objects.filter(session_key=stored_session_key).delete()
                messages.warning(request, 'Vous avez été déconnecté car quelqu\'un s\'est connecté avec votre compte.')
                logout(request)
                return self.get_response(request)
            
            request.user.session_key = current_session_key
            request.user.save()
        
        return self.get_response(request)
