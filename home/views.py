# home/views.py - Version nettoyée sans Reservation
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model

# Import sécurisé des services
try:
    from services.maison_service import MaisonService
    MAISON_SERVICE_AVAILABLE = True
except ImportError:
    MAISON_SERVICE_AVAILABLE = False
    print("⚠️ MaisonService non disponible - utilisation des fallbacks")

from .models import Maison, CategorieMaison, Ville, PhotoMaison

User = get_user_model()


def index(request):
    """Vue principale de la page d'accueil - NETTOYÉE"""
    
    # Récupérer les maisons featured disponibles pour tous
    maisons_featured = Maison.objects.filter(
        featured=True, 
        disponible=True
    ).select_related('ville', 'categorie', 'gestionnaire').prefetch_related('photos')[:6]
    
    # Statistiques pour la section stats (sans réservations pour l'instant)
    stats = {
        'total_maisons': Maison.objects.filter(disponible=True).count(),
        'total_villes': Ville.objects.count(),
        'total_reservations': 0,  # TODO: À rétablir avec l'app reservations
        'satisfaction_client': 98,  # Peut être calculé dynamiquement plus tard
    }
    
    # Catégories populaires
    categories = CategorieMaison.objects.annotate(
        nombre_maisons=Count('maison', filter=Q(maison__disponible=True))
    ).filter(nombre_maisons__gt=0)[:4]
    
    # Villes populaires
    villes_populaires = Ville.objects.annotate(
        nombre_maisons=Count('maison', filter=Q(maison__disponible=True))
    ).filter(nombre_maisons__gt=0).order_by('-nombre_maisons')[:6]
    
    context = {
        'maisons_featured': maisons_featured,
        'stats': stats,
        'categories': categories,
        'villes_populaires': villes_populaires,
        'page_title': 'Accueil - RepAvi Lodges',
        'meta_description': 'Trouvez et réservez la maison meublée parfaite pour vos séjours. RepAvi Lodges - Douala, Cameroun.',
        'user_authenticated': request.user.is_authenticated,
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
    }
    
    return render(request, 'home/index.html', context)


class MaisonListView(ListView):
    """Vue liste des maisons avec filtres - NETTOYÉE"""
    model = Maison
    template_name = 'home/maisons_list.html'
    context_object_name = 'maisons'
    paginate_by = 12
    
    def get_queryset(self):
        # Utiliser le service si disponible, sinon fallback
        user = self.request.user if self.request.user.is_authenticated else None
        
        if MAISON_SERVICE_AVAILABLE and user:
            try:
                queryset = MaisonService.get_maisons_for_user(user)
            except Exception:
                queryset = self._get_fallback_queryset(user)
        else:
            queryset = self._get_fallback_queryset(user)
        
        queryset = queryset.select_related('ville', 'categorie', 'gestionnaire').prefetch_related('photos')
        
        # Filtres de recherche
        search = self.request.GET.get('search')
        ville_id = self.request.GET.get('ville')
        categorie_id = self.request.GET.get('categorie')
        capacite = self.request.GET.get('capacite')
        prix_min = self.request.GET.get('prix_min')
        prix_max = self.request.GET.get('prix_max')
        
        # Appliquer les filtres manuellement
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) |
                Q(description__icontains=search) |
                Q(ville__nom__icontains=search)
            )
        
        if ville_id:
            queryset = queryset.filter(ville_id=ville_id)
        if categorie_id:
            queryset = queryset.filter(categorie_id=categorie_id)
        if capacite:
            queryset = queryset.filter(capacite_personnes__gte=capacite)
        if prix_min:
            queryset = queryset.filter(prix_par_nuit__gte=prix_min)
        if prix_max:
            queryset = queryset.filter(prix_par_nuit__lte=prix_max)
        
        # Tri
        sort_by = self.request.GET.get('sort', '-date_creation')
        valid_sorts = [
            'prix_par_nuit', '-prix_par_nuit',
            'capacite_personnes', '-capacite_personnes',
            'date_creation', '-date_creation'
        ]
        if sort_by in valid_sorts:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def _get_fallback_queryset(self, user):
        """Fallback pour récupérer les maisons selon les permissions"""
        if not user or not user.is_authenticated:
            return Maison.objects.filter(disponible=True)
        
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            return Maison.objects.all()
        elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
            return Maison.objects.filter(gestionnaire=user)
        else:
            return Maison.objects.filter(disponible=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['villes'] = Ville.objects.all().order_by('nom')
        context['categories'] = CategorieMaison.objects.all()
        context['current_filters'] = self.request.GET
        context['user_role'] = getattr(self.request.user, 'role', None) if self.request.user.is_authenticated else None
        return context


class MaisonDetailView(DetailView):
    """Vue détail d'une maison - NETTOYÉE"""
    model = Maison
    template_name = 'home/maison_detail.html'
    context_object_name = 'maison'
    slug_field = 'slug'
    
    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None
        
        if MAISON_SERVICE_AVAILABLE and user:
            try:
                return MaisonService.get_maisons_for_user(user)
            except Exception:
                pass
        
        # Fallback
        if not user or not user.is_authenticated:
            return Maison.objects.filter(disponible=True)
        elif hasattr(user, 'is_super_admin') and user.is_super_admin():
            return Maison.objects.all()
        elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
            return Maison.objects.filter(gestionnaire=user)
        else:
            return Maison.objects.filter(disponible=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Photos de la maison
        context['photos'] = self.object.photos.all().order_by('ordre')
        
        # Maisons similaires
        context['maisons_similaires'] = Maison.objects.filter(
            ville=self.object.ville,
            disponible=True
        ).exclude(id=self.object.id).select_related('ville', 'categorie')[:3]
        
        # Meubles de la maison (NOUVEAU)
        try:
            from meubles.models import Meuble
            context['meubles'] = self.object.meubles.all().select_related('type_meuble')
            context['meubles_par_piece'] = {}
            for meuble in context['meubles']:
                piece = meuble.get_piece_display()
                if piece not in context['meubles_par_piece']:
                    context['meubles_par_piece'][piece] = []
                context['meubles_par_piece'][piece].append(meuble)
        except ImportError:
            context['meubles'] = []
            context['meubles_par_piece'] = {}
        
        # Permissions pour les boutons d'action
        user = self.request.user
        context['can_reserve'] = user.is_authenticated and hasattr(user, 'is_client') and user.is_client()
        context['can_manage'] = user.is_authenticated and self.object.can_be_managed_by(user)
        context['user_role'] = getattr(user, 'role', None) if user.is_authenticated else None
        
        # Informations de contact du gestionnaire (pour les clients)
        if user.is_authenticated and hasattr(user, 'is_client') and user.is_client():
            gestionnaire = self.object.gestionnaire
            context['gestionnaire_info'] = {
                'nom': getattr(gestionnaire, 'nom_complet', f"{gestionnaire.first_name} {gestionnaire.last_name}"),
                'telephone': getattr(gestionnaire, 'telephone', ''),
                'email': gestionnaire.email if getattr(gestionnaire, 'email_verifie', True) else None,
            }
        
        return context


@require_http_methods(["GET"])
def recherche_ajax(request):
    """Recherche AJAX pour l'autocomplétion - NETTOYÉE"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        query = request.GET.get('q', '')
        
        if len(query) >= 2:
            user = self.request.user if request.user.is_authenticated else None
            
            # Recherche dans les maisons
            if MAISON_SERVICE_AVAILABLE and user:
                try:
                    maisons = MaisonService.search_maisons(query, user)[:5]
                except Exception:
                    maisons = Maison.objects.filter(
                        Q(nom__icontains=query) |
                        Q(description__icontains=query),
                        disponible=True
                    )[:5]
            else:
                maisons = Maison.objects.filter(
                    Q(nom__icontains=query) |
                    Q(description__icontains=query),
                    disponible=True
                )[:5]
            
            # Recherche dans les villes
            villes = Ville.objects.filter(nom__icontains=query)[:5]
            
            results = {
                'maisons': [
                    {
                        'id': m.id,
                        'nom': m.nom,
                        'ville': str(m.ville),
                        'prix': float(m.prix_par_nuit),
                        'url': m.get_absolute_url(),
                        'gestionnaire': getattr(m.gestionnaire, 'nom_complet', f"{m.gestionnaire.first_name} {m.gestionnaire.last_name}"),
                        'disponible': m.disponible
                    } for m in maisons
                ],
                'villes': [
                    {
                        'id': v.id,
                        'nom': str(v),
                        'url': f'/maisons/?ville={v.id}'
                    } for v in villes
                ]
            }
            
            return JsonResponse(results)
    
    return JsonResponse({'maisons': [], 'villes': []})


def contact(request):
    """Page de contact - NETTOYÉE"""
    if request.method == 'POST':
        # Traitement du formulaire de contact
        nom = request.POST.get('nom')
        email = request.POST.get('email')
        sujet = request.POST.get('sujet')
        message = request.POST.get('message')
        
        # TODO: Intégrer avec le service de notification (app notifications)
        # NotificationService.send_contact_message(nom, email, sujet, message)
        
        messages.success(request, 'Votre message a été envoyé avec succès!')
        
    context = {
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
    }
    
    return render(request, 'home/contact.html', context)


def apropos(request):
    """Page à propos avec statistiques - NETTOYÉE"""
    stats = {
        'annee_creation': 2020,
        'maisons_disponibles': Maison.objects.filter(disponible=True).count(),
        'villes_couvertes': Ville.objects.count(),
        'clients_satisfaits': 10000,  # TODO: calculer depuis l'app reservations
        'gestionnaires_partenaires': User.objects.filter(role='GESTIONNAIRE').count() if hasattr(User, 'role') else 0,
    }
    
    # Témoignages de clients (à implémenter avec le système d'avis)
    # testimonials = AvisService.get_featured_testimonials()
    
    context = {
        'stats': stats,
        'page_title': 'À propos - RepAvi Lodges',
        'meta_description': 'Découvrez l\'histoire et les valeurs de RepAvi Lodges, votre partenaire de confiance pour la location de maisons d\'exception au Cameroun.',
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
    }
    
    return render(request, 'home/apropos.html', context)


# ======== API ENDPOINTS POUR APPLICATIONS FUTURES ========

@require_http_methods(["GET"])
def api_maisons_disponibles(request):
    """API endpoint pour récupérer les maisons disponibles"""
    maisons = Maison.objects.filter(disponible=True).select_related('ville', 'categorie')
    
    data = []
    for maison in maisons:
        data.append({
            'id': maison.id,
            'nom': maison.nom,
            'numero': maison.numero,
            'ville': maison.ville.nom,
            'prix_par_nuit': float(maison.prix_par_nuit),
            'capacite': maison.capacite_personnes,
            'statut_occupation': maison.statut_occupation,
            'photo_principale': maison.photo_principale.url if maison.photo_principale else None,
        })
    
    return JsonResponse({'maisons': data})


# ======== VUES POUR L'INVENTAIRE DES MEUBLES ========

@login_required
def maison_inventaire(request, slug):
    """Vue pour l'inventaire des meubles d'une maison"""
    maison = get_object_or_404(Maison, slug=slug)
    
    # Vérifier les permissions
    if not maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour voir l'inventaire de cette maison.")
        return redirect('home:maison_detail', slug=slug)
    
    try:
        from meubles.models import Meuble, InventaireMaison
        
        # Meubles de la maison
        meubles = maison.meubles.all().select_related('type_meuble')
        
        # Statistiques
        stats = {
            'total': meubles.count(),
            'bon_etat': meubles.filter(etat='bon').count(),
            'defectueux': meubles.filter(etat='defectueux').count(),
            'usage': meubles.filter(etat='usage').count(),
        }
        
        # Dernier inventaire
        dernier_inventaire = maison.inventaires.first()
        
        context = {
            'maison': maison,
            'meubles': meubles,
            'stats': stats,
            'dernier_inventaire': dernier_inventaire,
        }
        
        return render(request, 'home/maison_inventaire.html', context)
        
    except ImportError:
        messages.error(request, "Le module de gestion des meubles n'est pas disponible.")
        return redirect('home:maison_detail', slug=slug)