# home/views.py - Version adaptée avec nouveaux rôles et services
from datetime import timezone
from django.forms import ValidationError
from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from home.forms import User
from services.maison_service import MaisonService
from services.reservation_service import ReservationService
from services.statistics_service import StatisticsService
from .models import Maison, CategorieMaison, Ville, PhotoMaison, Reservation
import json

def index(request):
    """Vue principale de la page d'accueil - ADAPTÉE"""
    
    # Récupérer les maisons featured disponibles pour tous
    maisons_featured = Maison.objects.filter(
        featured=True, 
        disponible=True
    ).select_related('ville', 'categorie', 'gestionnaire').prefetch_related('photos')[:6]
    
    # Statistiques pour la section stats
    stats = {
        'total_maisons': Maison.objects.filter(disponible=True).count(),
        'total_villes': Ville.objects.count(),
        'total_reservations': Reservation.objects.filter(statut='confirmee').count(),
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
        'page_title': 'Accueil - RepAvi',
        'meta_description': 'Trouvez et réservez la maison meublée parfaite pour vos vacances. Plus de 250 maisons vérifiées dans toute la France.',
        'user_authenticated': request.user.is_authenticated,
        'user_role': request.user.role if request.user.is_authenticated else None,
    }
    
    return render(request, 'home/index.html', context)


class MaisonListView(ListView):
    """Vue liste des maisons avec filtres - ADAPTÉE"""
    model = Maison
    template_name = 'home/maisons_list.html'
    context_object_name = 'maisons'
    paginate_by = 12
    
    def get_queryset(self):
        # Utiliser le service pour récupérer les maisons selon les permissions
        user = self.request.user if self.request.user.is_authenticated else None
        
        # Pour les visiteurs non connectés, montrer seulement les maisons disponibles
        if not user or not user.is_authenticated:
            queryset = Maison.objects.filter(disponible=True)
        else:
            queryset = MaisonService.get_maisons_for_user(user)
        
        queryset = queryset.select_related('ville', 'categorie', 'gestionnaire').prefetch_related('photos')
        
        # Filtres de recherche
        search = self.request.GET.get('search')
        ville_id = self.request.GET.get('ville')
        categorie_id = self.request.GET.get('categorie')
        capacite = self.request.GET.get('capacite')
        prix_min = self.request.GET.get('prix_min')
        prix_max = self.request.GET.get('prix_max')
        
        # Utiliser le service de recherche si des filtres sont appliqués
        if any([search, ville_id, categorie_id, capacite, prix_min, prix_max]):
            filters = {}
            if ville_id:
                filters['ville'] = ville_id
            if categorie_id:
                filters['categorie'] = categorie_id
            if capacite:
                filters['capacite_min'] = capacite
            if prix_min:
                filters['prix_min'] = prix_min
            if prix_max:
                filters['prix_max'] = prix_max
            
            queryset = MaisonService.search_maisons(search or '', user, filters)
        
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['villes'] = Ville.objects.all().order_by('nom')
        context['categories'] = CategorieMaison.objects.all()
        context['current_filters'] = self.request.GET
        context['user_role'] = self.request.user.role if self.request.user.is_authenticated else None
        return context


class MaisonDetailView(DetailView):
    """Vue détail d'une maison - ADAPTÉE"""
    model = Maison
    template_name = 'home/maison_detail.html'
    context_object_name = 'maison'
    slug_field = 'slug'
    
    def get_queryset(self):
        # Utiliser le service pour vérifier les permissions
        user = self.request.user if self.request.user.is_authenticated else None
        if user:
            return MaisonService.get_maisons_for_user(user)
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
        
        # Données du calendrier pour les disponibilités
        context['calendar_data'] = ReservationService.get_calendar_data(self.object)
        
        # Permissions pour les boutons d'action
        user = self.request.user
        context['can_reserve'] = user.is_authenticated and user.is_client()
        context['can_manage'] = user.is_authenticated and self.object.can_be_managed_by(user)
        context['user_role'] = user.role if user.is_authenticated else None
        
        # Informations de contact du gestionnaire (pour les clients)
        if user.is_authenticated and user.is_client():
            gestionnaire = self.object.gestionnaire
            context['gestionnaire_info'] = {
                'nom': gestionnaire.nom_complet,
                'telephone': gestionnaire.telephone,
                'email': gestionnaire.email if gestionnaire.email_verifie else None,
            }
        
        return context


@require_http_methods(["GET"])
def recherche_ajax(request):
    """Recherche AJAX pour l'autocomplétion - ADAPTÉE"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        query = request.GET.get('q', '')
        
        if len(query) >= 2:
            user = request.user if request.user.is_authenticated else None
            
            # Utiliser le service de recherche
            maisons = MaisonService.search_maisons(query, user)[:5]
            
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
                        'gestionnaire': m.gestionnaire.nom_complet,
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


@login_required
@require_http_methods(["POST"])
def create_reservation_ajax(request):
    """Créer une réservation via AJAX - NOUVELLE"""
    if not request.user.is_client():
        return JsonResponse({
            'success': False,
            'error': 'Seuls les clients peuvent faire des réservations.'
        })
    
    try:
        maison_id = request.POST.get('maison_id')
        date_debut = request.POST.get('date_debut')
        date_fin = request.POST.get('date_fin')
        nombre_personnes = request.POST.get('nombre_personnes')
        message = request.POST.get('message', '')
        
        # Validation basique
        if not all([maison_id, date_debut, date_fin, nombre_personnes]):
            return JsonResponse({
                'success': False,
                'error': 'Tous les champs sont requis.'
            })
        
        maison = get_object_or_404(Maison, id=maison_id)
        
        # Convertir les dates
        from datetime import datetime
        date_debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
        
        # Utiliser le service pour créer la réservation
        reservation_data = {
            'date_debut': date_debut,
            'date_fin': date_fin,
            'nombre_personnes': int(nombre_personnes),
            'message': message,
            'telephone': request.user.telephone or ''
        }
        
        reservation = ReservationService.create_reservation(
            request.user, maison, reservation_data
        )
        
        return JsonResponse({
            'success': True,
            'reservation_id': reservation.id,
            'message': 'Réservation créée avec succès! Le gestionnaire sera notifié.'
        })
        
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Erreur lors de la création de la réservation.'
        })


def contact(request):
    """Page de contact - ADAPTÉE"""
    if request.method == 'POST':
        # Traitement du formulaire de contact
        nom = request.POST.get('nom')
        email = request.POST.get('email')
        sujet = request.POST.get('sujet')
        message = request.POST.get('message')
        
        # TODO: Intégrer avec le service de notification
        # NotificationService.send_contact_message(nom, email, sujet, message)
        
        messages.success(request, 'Votre message a été envoyé avec succès!')
        
    context = {
        'user_role': request.user.role if request.user.is_authenticated else None,
    }
    
    return render(request, 'home/contact.html', context)


def apropos(request):
    """Page à propos avec statistiques - ADAPTÉE"""
    stats = {
        'annee_creation': 2020,
        'maisons_disponibles': Maison.objects.filter(disponible=True).count(),
        'villes_couvertes': Ville.objects.count(),
        'clients_satisfaits': Reservation.objects.filter(statut='terminee').count() or 10000,
        'gestionnaires_partenaires': User.objects.filter(role='GESTIONNAIRE').count(),
    }
    
    # Témoignages de clients (à implémenter avec le système d'avis)
    # testimonials = AvisService.get_featured_testimonials()
    
    context = {
        'stats': stats,
        'page_title': 'À propos - RepAvi',
        'meta_description': 'Découvrez l\'histoire et les valeurs de RepAvi, votre partenaire de confiance pour la location de maisons d\'exception.',
        'user_role': request.user.role if request.user.is_authenticated else None,
    }
    
    return render(request, 'home/apropos.html', context)


# ======== VUES POUR GESTIONNAIRES ========

@login_required
def gestionnaire_dashboard(request):
    """Dashboard spécifique pour gestionnaires - NOUVELLE"""
    if not request.user.is_gestionnaire():
        messages.error(request, "Accès réservé aux gestionnaires.")
        return redirect('home:index')
    
    # Utiliser le service de statistiques
    stats = StatisticsService.get_dashboard_stats(request.user)
    
    # Réservations récentes
    reservations_recentes = ReservationService.get_reservations_for_user(request.user)[:5]
    
    # Maisons les plus populaires
    maisons_populaires = Maison.objects.filter(
        gestionnaire=request.user
    ).annotate(
        nb_reservations=Count('reservations')
    ).order_by('-nb_reservations')[:5]
    
    context = {
        'stats': stats,
        'reservations_recentes': reservations_recentes,
        'maisons_populaires': maisons_populaires,
        'calendar_data': [],  # TODO: Implémenter calendrier global
    }
    
    return render(request, 'home/gestionnaire_dashboard.html', context)


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
            'ville': maison.ville.nom,
            'prix_par_nuit': float(maison.prix_par_nuit),
            'capacite': maison.capacite_personnes,
            'photo_principale': maison.photo_principale.url if maison.photo_principale else None,
        })
    
    return JsonResponse({'maisons': data})


@require_http_methods(["GET"]) 
def api_disponibilites(request, maison_id):
    """API endpoint pour vérifier les disponibilités d'une maison"""
    try:
        maison = get_object_or_404(Maison, id=maison_id)
        
        # Récupérer les paramètres de date
        year = int(request.GET.get('year', timezone.now().year))
        month = int(request.GET.get('month', timezone.now().month))
        
        calendar_data = ReservationService.get_calendar_data(maison, year, month)
        
        return JsonResponse({
            'success': True,
            'calendar_data': calendar_data,
            'maison': {
                'id': maison.id,
                'nom': maison.nom,
                'disponible': maison.disponible
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })