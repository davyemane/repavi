import threading
from django.utils.deprecation import MiddlewareMixin

# Thread local pour stocker l'utilisateur actuel
_user = threading.local()

def get_current_user():
    return getattr(_user, 'value', None)

def set_current_user(user):
    _user.value = user

class AuditMiddleware(MiddlewareMixin):
    """Middleware pour capturer l'utilisateur dans les signaux"""
    
    def process_request(self, request):
        # Stocker l'utilisateur dans thread local
        if hasattr(request, 'user') and request.user.is_authenticated:
            set_current_user(request.user)
        else:
            set_current_user(None)
            
        # Données de la requête
        request._audit_data = {
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'url': request.get_full_path(),
            'method': request.method,
        }
        return None
    
    def process_response(self, request, response):
        # Log des actions CRUD réussies
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and 200 <= response.status_code < 300:
                self.log_crud_action(request, response)
        
        # Nettoyer le thread local
        set_current_user(None)
        return response
    
    def log_crud_action(self, request, response):
        """Log action via middleware"""
        try:
            from .models import ActionLog
            
            action_map = {
                'POST': 'create',
                'PUT': 'update', 
                'PATCH': 'update',
                'DELETE': 'delete'
            }
            
            action = action_map.get(request.method)
            if not action:
                return
                
            model_name = self.extract_model_from_url(request.path)
            
            ActionLog.objects.create(
                utilisateur=request.user,
                action=action,
                model_name=model_name,
                object_repr=f"Action {action} via {request.method}",
                ip_address=request._audit_data['ip_address'],
                user_agent=request._audit_data['user_agent'],
                url=request._audit_data['url'],
                method=request.method,
                details=f'{{"status_code": {response.status_code}}}',
            )
        except Exception:
            pass
    
    def extract_model_from_url(self, path):
        """Extraire le modèle depuis l'URL"""
        url_parts = path.strip('/').split('/')
        
        model_mapping = {
            'reservations': 'Reservation',
            'clients': 'Client',
            'appartements': 'Appartement', 
            'paiements': 'Paiement',
            'inventaire': 'Equipement',
            'menage': 'TacheMenage',
            'users': 'User',
        }
        
        for part in url_parts:
            if part in model_mapping:
                return model_mapping[part]
        return 'Unknown'
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
