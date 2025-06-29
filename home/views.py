# home/views.py - Version complète
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, Count, Sum
from django.db import models
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, Http404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.utils.text import slugify
import json
import csv

# Import sécurisé des services
try:
    from services.maison_service import MaisonService
    MAISON_SERVICE_AVAILABLE = True
except ImportError:
    MAISON_SERVICE_AVAILABLE = False
    print("⚠️ MaisonService non disponible - utilisation des fallbacks")

# Import sécurisé du module reservations
try:
    from reservations.models import Reservation
    RESERVATIONS_AVAILABLE = True
except ImportError:
    RESERVATIONS_AVAILABLE = False
    print("⚠️ Module réservations non disponible")

from .models import Maison, CategorieMaison, Ville, PhotoMaison

User = get_user_model()



# ======== MIXINS POUR LES PERMISSIONS ========

class GestionnaireRequiredMixin(UserPassesTestMixin):
    """Mixin pour vérifier que l'utilisateur est gestionnaire ou super admin"""
    
    def test_func(self):
        user = self.request.user
        return (hasattr(user, 'is_gestionnaire') and user.is_gestionnaire()) or \
               (hasattr(user, 'is_super_admin') and user.is_super_admin()) or \
               user.is_superuser


class MaisonOwnerMixin(UserPassesTestMixin):
    """Mixin pour vérifier que l'utilisateur peut gérer cette maison"""
    
    def test_func(self):
        maison = self.get_object()
        return maison.can_be_managed_by(self.request.user)


# ======== PAGES PUBLIQUES ========

def index(request):
    """Vue principale de la page d'accueil"""
    
    try:
        # Récupérer les maisons featured disponibles pour tous
        maisons_featured = Maison.objects.filter(
            featured=True, 
            disponible=True
        ).select_related('ville', 'categorie').prefetch_related('photos')[:6]
        
        # Statistiques pour la section stats
        stats = {
            'total_maisons': Maison.objects.filter(disponible=True).count(),
            'total_villes': Ville.objects.count(),
            'total_reservations': 0,
            'satisfaction_client': 98,
        }
        
        # Calculer les statistiques de réservations si disponible
        if RESERVATIONS_AVAILABLE:
            try:
                from reservations.models import Reservation
                stats['total_reservations'] = Reservation.objects.filter(
                    statut__in=['confirmee', 'terminee']
                ).count()
            except ImportError:
                stats['total_reservations'] = 0
        
        # Catégories populaires
        categories = CategorieMaison.objects.annotate(
            nombre_maisons=Count('maison', filter=Q(maison__disponible=True))
        ).filter(nombre_maisons__gt=0)[:4]
        
        # Villes populaires
        villes_populaires = Ville.objects.annotate(
            nombre_maisons=Count('maison', filter=Q(maison__disponible=True))
        ).filter(nombre_maisons__gt=0).order_by('-nombre_maisons')[:6]
        
    except Exception as e:
        # En cas d'erreur (tables vides, etc.), utiliser des valeurs par défaut
        print(f"Erreur dans index: {e}")
        maisons_featured = []
        stats = {
            'total_maisons': 0,
            'total_villes': 0,
            'total_reservations': 0,
            'satisfaction_client': 98,
        }
        categories = []
        villes_populaires = []
    
    context = {
        'maisons_featured': maisons_featured,
        'stats': stats,
        'categories': categories,
        'villes_populaires': villes_populaires,
        'page_title': 'Accueil - RepAvi Lodges',
        'meta_description': 'Trouvez et réservez la maison meublée parfaite pour vos séjours. RepAvi Lodges - Douala, Cameroun.',
        'user_authenticated': request.user.is_authenticated,
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
        'reservations_available': RESERVATIONS_AVAILABLE,
    }
    
    return render(request, 'home/index.html', context)

def contact(request):
    """Page de contact"""
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
        'reservations_available': RESERVATIONS_AVAILABLE,
    }
    
    return render(request, 'home/contact.html', context)
def apropos(request):
    """Page à propos avec statistiques"""
    stats = {
        'annee_creation': 2020,
        'maisons_disponibles': Maison.objects.filter(disponible=True).count(),
        'villes_couvertes': Ville.objects.count(),
        'clients_satisfaits': 10000,
        'gestionnaires_partenaires': User.objects.filter(role='GESTIONNAIRE').count() if hasattr(User, 'role') else 0,
    }
    
    # Calculer les vraies statistiques si les réservations sont disponibles
    if RESERVATIONS_AVAILABLE:
        try:
            stats['clients_satisfaits'] = Reservation.objects.filter(
                statut='terminee'
            ).values('client').distinct().count()
        except:
            pass
    
    context = {
        'stats': stats,
        'page_title': 'À propos - RepAvi Lodges',
        'meta_description': 'Découvrez l\'histoire et les valeurs de RepAvi Lodges, votre partenaire de confiance pour la location de maisons d\'exception au Cameroun.',
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
        'reservations_available': RESERVATIONS_AVAILABLE,
    }
    
    return render(request, 'home/apropos.html', context)
# ======== MAISONS - CONSULTATION ========

class MaisonListView(ListView):
    """Vue liste des maisons avec filtres"""
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
        
        queryset = queryset.with_photos_and_details()
        
        # Filtres de recherche
        search = self.request.GET.get('search')
        ville_id = self.request.GET.get('ville')
        categorie_id = self.request.GET.get('categorie')
        capacite = self.request.GET.get('capacite')
        prix_min = self.request.GET.get('prix_min')
        prix_max = self.request.GET.get('prix_max')
        disponible_reservation = self.request.GET.get('disponible_reservation')
        
        # Appliquer les filtres
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
        
        # Filtre pour les maisons disponibles à la réservation
        if disponible_reservation == '1':
            queryset = queryset.filter(disponible=True, statut_occupation='libre')
        
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
        context['reservations_available'] = RESERVATIONS_AVAILABLE
        return context


def maisons_disponibles_reservation(request):
    """Vue pour afficher les maisons disponibles à la réservation"""
    
    # Filtrer uniquement les maisons disponibles pour réservation
    maisons = Maison.objects.filter(
        disponible=True,
        statut_occupation='libre'
    ).with_photos_and_details()
    
    # Filtres de recherche
    search = request.GET.get('search')
    ville_id = request.GET.get('ville')
    categorie_id = request.GET.get('categorie')
    capacite = request.GET.get('capacite')
    prix_min = request.GET.get('prix_min')
    prix_max = request.GET.get('prix_max')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    # Appliquer les filtres
    if search:
        maisons = maisons.filter(
            Q(nom__icontains=search) |
            Q(description__icontains=search) |
            Q(ville__nom__icontains=search)
        )
    
    if ville_id:
        maisons = maisons.filter(ville_id=ville_id)
    if categorie_id:
        maisons = maisons.filter(categorie_id=categorie_id)
    if capacite:
        maisons = maisons.filter(capacite_personnes__gte=capacite)
    if prix_min:
        maisons = maisons.filter(prix_par_nuit__gte=prix_min)
    if prix_max:
        maisons = maisons.filter(prix_par_nuit__lte=prix_max)
    
    # Vérifier la disponibilité par dates si spécifiées
    if date_debut and date_fin and RESERVATIONS_AVAILABLE:
        try:
            from datetime import datetime
            debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
            fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
            
            # Filtrer les maisons qui n'ont pas de réservations conflictuelles
            maisons_ids = []
            for maison in maisons:
                if Reservation.objects.verifier_disponibilite(maison, debut, fin):
                    maisons_ids.append(maison.id)
            
            maisons = maisons.filter(id__in=maisons_ids)
        except ValueError:
            pass  # Dates invalides, ignorer le filtre
    
    # Pagination
    paginator = Paginator(maisons, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'maisons': page_obj.object_list,
        'villes': Ville.objects.all().order_by('nom'),
        'categories': CategorieMaison.objects.all(),
        'current_filters': request.GET,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'total_maisons': maisons.count(),
        'reservations_available': RESERVATIONS_AVAILABLE,
        'page_title': 'Maisons Disponibles à la Réservation',
    }
    
    return render(request, 'home/maisons_reservation.html', context)



class MaisonDetailView(DetailView):
    """Vue détail d'une maison"""
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
        return Maison.objects.accessible_to_user(user if user else None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Photos de la maison
        context['photos'] = self.object.photos.all().order_by('ordre')
        
        # Maisons similaires
        context['maisons_similaires'] = Maison.objects.filter(
            ville=self.object.ville,
            disponible=True
        ).exclude(id=self.object.id).with_photos_and_details()[:3]
        
        # Meubles de la maison
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
        
        # Vérification de disponibilité pour réservation
        context['disponible_reservation'] = (
            self.object.disponible and 
            self.object.statut_occupation == 'libre' and
            RESERVATIONS_AVAILABLE
        )
        
        # Informations de réservation
        if RESERVATIONS_AVAILABLE and context['disponible_reservation']:
            try:
                from datetime import date
                today = date.today()
                
                # Réservations actuelles ou futures
                reservations_actives = Reservation.objects.filter(
                    maison=self.object,
                    statut__in=['confirmee', 'en_attente'],
                    date_fin__gte=today
                ).order_by('date_debut')
                
                context['prochaines_reservations'] = reservations_actives[:3]
                context['maison_libre_maintenant'] = not reservations_actives.filter(
                    date_debut__lte=today,
                    date_fin__gte=today
                ).exists()
                
            except Exception:
                context['prochaines_reservations'] = []
                context['maison_libre_maintenant'] = True
        
        # Informations de contact du gestionnaire (pour les clients)
        if user.is_authenticated and hasattr(user, 'is_client') and user.is_client():
            gestionnaire = self.object.gestionnaire
            context['gestionnaire_info'] = {
                'nom': getattr(gestionnaire, 'nom_complet', f"{gestionnaire.first_name} {gestionnaire.last_name}"),
                'telephone': getattr(gestionnaire, 'telephone', ''),
                'email': gestionnaire.email if getattr(gestionnaire, 'email_verifie', True) else None,
            }
        
        context['reservations_available'] = RESERVATIONS_AVAILABLE
        
        return context

# ======== MAISONS - GESTION ========

class MaisonCreateView(LoginRequiredMixin, GestionnaireRequiredMixin, CreateView):
    """Vue pour créer une nouvelle maison"""
    model = Maison
    fields = ['nom', 'numero', 'ville', 'categorie', 'description', 'prix_par_nuit', 
              'capacite_personnes', 'nombre_chambres', 'nombre_salles_bain', 'superficie', 
              'adresse', 'disponible', 'featured', 'wifi', 'parking', 'piscine', 'jardin',
              'climatisation', 'lave_vaisselle', 'machine_laver', 'balcon', 'terrasse']
    template_name = 'home/maison_form.html'
    success_url = reverse_lazy('home:mes_maisons')
    
    def form_valid(self, form):
        # Assigner le gestionnaire connecté
        form.instance.gestionnaire = self.request.user
        
        # Auto-génération du slug
        if not form.instance.slug:
            form.instance.slug = slugify(f"{form.instance.numero}-{form.instance.nom}")
        
        messages.success(self.request, f'La maison "{form.instance.nom}" a été créée avec succès!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Ajouter une nouvelle maison'
        context['button_text'] = 'Créer la maison'
        context['villes'] = Ville.objects.all().order_by('nom')
        context['categories'] = CategorieMaison.objects.all().order_by('nom')
        return context


class MaisonUpdateView(LoginRequiredMixin, MaisonOwnerMixin, UpdateView):
    """Vue pour modifier une maison"""
    model = Maison
    fields = ['nom', 'numero', 'ville', 'categorie', 'description', 'prix_par_nuit', 
              'capacite_personnes', 'nombre_chambres', 'nombre_salles_bain', 'superficie', 
              'adresse', 'disponible', 'featured', 'statut_occupation', 'wifi', 'parking', 
              'piscine', 'jardin', 'climatisation', 'lave_vaisselle', 'machine_laver', 
              'balcon', 'terrasse']
    template_name = 'home/maison_form.html'
    slug_field = 'slug'
    
    def get_queryset(self):
        """Seul le gestionnaire propriétaire ou super admin peut modifier"""
        return Maison.objects.accessible_to_user(self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, f'La maison "{form.instance.nom}" a été modifiée avec succès!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return self.object.get_absolute_url()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Modifier {self.object.nom}'
        context['button_text'] = 'Sauvegarder les modifications'
        context['villes'] = Ville.objects.all().order_by('nom')
        context['categories'] = CategorieMaison.objects.all().order_by('nom')
        context['reservations_available'] = RESERVATIONS_AVAILABLE
        return context

class MaisonDeleteView(LoginRequiredMixin, MaisonOwnerMixin, DeleteView):
    """Vue pour supprimer une maison"""
    model = Maison
    template_name = 'home/maison_confirm_delete.html'
    slug_field = 'slug'
    success_url = reverse_lazy('home:mes_maisons')
    
    def get_queryset(self):
        """Seul le gestionnaire propriétaire ou super admin peut supprimer"""
        return Maison.objects.accessible_to_user(self.request.user)
    
    def delete(self, request, *args, **kwargs):
        maison = self.get_object()
        nom_maison = maison.nom
        result = super().delete(request, *args, **kwargs)
        messages.success(request, f'La maison "{nom_maison}" a été supprimée avec succès!')
        return result

@login_required
def statistiques_generales(request):
    """Vue des statistiques générales pour les gestionnaires et admins"""
    user = request.user
    
    # Vérifier les permissions
    if not ((hasattr(user, 'is_gestionnaire') and user.is_gestionnaire()) or 
            (hasattr(user, 'is_super_admin') and user.is_super_admin()) or
            user.is_superuser):
        messages.error(request, "Accès non autorisé.")
        return redirect('home:index')
    
    # Récupérer les maisons selon les permissions
    maisons = Maison.objects.accessible_to_user(user)
    
    # Statistiques de base
    stats = {
        'total_maisons': maisons.count(),
        'maisons_disponibles': maisons.filter(disponible=True).count(),
        'maisons_occupees': maisons.filter(statut_occupation='occupe').count(),
        'maisons_maintenance': maisons.filter(statut_occupation='maintenance').count(),
        'maisons_featured': maisons.filter(featured=True).count(),
        'total_photos': PhotoMaison.objects.filter(maison__in=maisons).count(),
        'prix_moyen': maisons.aggregate(Avg('prix_par_nuit'))['prix_par_nuit__avg'] or 0,
        'capacite_totale': maisons.aggregate(Sum('capacite_personnes'))['capacite_personnes__sum'] or 0,
    }
    
    # Évolution mensuelle (simulée pour l'instant)
    import datetime
    from datetime import timedelta
    
    mois_actuels = []
    for i in range(6):
        date = datetime.date.today() - timedelta(days=30*i)
        mois_actuels.append({
            'mois': date.strftime('%B %Y'),
            'nouvelles_maisons': maisons.filter(
                date_creation__year=date.year,
                date_creation__month=date.month
            ).count()
        })
    
    # Répartition par statut
    repartition_statuts = []
    for statut_code, statut_label in Maison.STATUT_OCCUPATION_CHOICES:
        count = maisons.filter(statut_occupation=statut_code).count()
        if count > 0:
            repartition_statuts.append({
                'statut': statut_label,
                'count': count,
                'pourcentage': round((count / stats['total_maisons']) * 100, 1) if stats['total_maisons'] > 0 else 0
            })
    
    # Top villes
    top_villes = maisons.values('ville__nom').annotate(
        count=Count('id'),
        revenus_potentiels=Sum('prix_par_nuit')
    ).order_by('-count')[:5]
    
    context = {
        'stats': stats,
        'mois_actuels': reversed(mois_actuels),
        'repartition_statuts': repartition_statuts,
        'top_villes': top_villes,
        'user_role': getattr(user, 'role', None),
    }
    
    return render(request, 'home/statistiques_generales.html', context)


@login_required
@require_http_methods(["POST"])
def toggle_maison_disponibilite(request, slug):
    """Basculer la disponibilité d'une maison"""
    maison = get_object_or_404(Maison, slug=slug)
    
    # Vérifier les permissions
    if not maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour modifier cette maison.")
        return redirect('home:maison_detail', slug=slug)
    
    # Basculer la disponibilité
    maison.disponible = not maison.disponible
    maison.save()
    
    status = "disponible" if maison.disponible else "indisponible"
    messages.success(request, f'La maison "{maison.nom}" est maintenant {status}.')
    
    return redirect('home:maison_detail', slug=slug)


# ======== GESTION DES PHOTOS ========

class PhotosListView(LoginRequiredMixin, GestionnaireRequiredMixin, ListView):
    """Vue pour lister toutes les photos du gestionnaire"""
    model = PhotoMaison
    template_name = 'home/photos_list.html'
    context_object_name = 'photos'
    paginate_by = 20
    
    def get_queryset(self):
        """Récupérer seulement les photos des maisons du gestionnaire"""
        user = self.request.user
        if hasattr(user, 'is_super_admin') and user.is_super_admin():
            return PhotoMaison.objects.all().select_related('maison').order_by('-date_ajout')
        elif hasattr(user, 'is_gestionnaire') and user.is_gestionnaire():
            return PhotoMaison.objects.filter(
                maison__gestionnaire=user
            ).select_related('maison').order_by('-date_ajout')
        else:
            return PhotoMaison.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_photos'] = self.get_queryset().count()
        context['maisons'] = Maison.objects.accessible_to_user(self.request.user)
        return context


class MaisonPhotosView(LoginRequiredMixin, MaisonOwnerMixin, DetailView):
    """Vue pour gérer les photos d'une maison"""
    model = Maison
    template_name = 'home/maison_photos.html'
    slug_field = 'slug'
    context_object_name = 'maison'
    
    def get_queryset(self):
        return Maison.objects.accessible_to_user(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['photos'] = self.object.photos.all().order_by('ordre')
        return context


@login_required
@require_http_methods(["POST"])
def ajouter_photo_maison(request, slug):
    """Ajouter une photo à une maison"""
    maison = get_object_or_404(Maison, slug=slug)
    
    if not maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour modifier cette maison.")
        return redirect('home:maison_detail', slug=slug)
    
    if 'photo' in request.FILES:
        photo = PhotoMaison.objects.create(
            maison=maison,
            image=request.FILES['photo'],
            titre=request.POST.get('titre', ''),
            type_photo=request.POST.get('type_photo', 'autre'),
            ordre=maison.photos.count() + 1
        )
        messages.success(request, 'Photo ajoutée avec succès!')
    else:
        messages.error(request, 'Aucune photo sélectionnée.')
    
    return redirect('home:maison_photos', slug=slug)


@login_required
@require_http_methods(["POST"])
def supprimer_photo_maison(request, photo_id):
    """Supprimer une photo de maison"""
    photo = get_object_or_404(PhotoMaison, id=photo_id)
    
    if not photo.maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour modifier cette maison.")
        return redirect('home:maison_detail', slug=photo.maison.slug)
    
    maison_slug = photo.maison.slug
    photo.delete()
    messages.success(request, 'Photo supprimée avec succès!')
    
    return redirect('home:maison_photos', slug=maison_slug)


@login_required
@require_http_methods(["POST"])
def definir_photo_principale(request, photo_id):
    """Définir une photo comme photo principale"""
    photo = get_object_or_404(PhotoMaison, id=photo_id)
    
    if not photo.maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour modifier cette maison.")
        return redirect('home:maison_detail', slug=photo.maison.slug)
    
    # Retirer le statut principal des autres photos
    PhotoMaison.objects.filter(maison=photo.maison).update(principale=False)
    
    # Définir cette photo comme principale
    photo.principale = True
    photo.save()
    
    messages.success(request, 'Photo principale définie avec succès!')
    return redirect('home:maison_photos', slug=photo.maison.slug)


# ======== DASHBOARD GESTIONNAIRE ========


class GestionnaireMaisonsView(LoginRequiredMixin, GestionnaireRequiredMixin, ListView):
    """Liste des maisons du gestionnaire"""
    model = Maison
    template_name = 'home/gestionnaire_maisons.html'
    context_object_name = 'maisons'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Maison.objects.accessible_to_user(self.request.user)
        
        # Filtres optionnels
        statut = self.request.GET.get('statut')
        if statut:
            queryset = queryset.filter(statut_occupation=statut)
        
        disponible = self.request.GET.get('disponible')
        if disponible == '1':
            queryset = queryset.filter(disponible=True)
        elif disponible == '0':
            queryset = queryset.filter(disponible=False)
        
        return queryset.order_by('-date_creation')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_filters'] = self.request.GET
        context['statuts'] = Maison.STATUT_OCCUPATION_CHOICES
        return context


@login_required
def initier_reservation(request, maison_slug):
    """Initier une réservation pour une maison"""
    
    if not RESERVATIONS_AVAILABLE:
        messages.error(request, "Le système de réservation n'est pas disponible.")
        return redirect('home:maison_detail', slug=maison_slug)
    
    # Vérifier que l'utilisateur peut faire des réservations
    if not (hasattr(request.user, 'is_client') and request.user.is_client()):
        messages.error(request, "Seuls les clients peuvent effectuer des réservations.")
        return redirect('home:maison_detail', slug=maison_slug)
    
    maison = get_object_or_404(Maison, slug=maison_slug, disponible=True)
    
    # Récupérer les paramètres de la requête
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    nombre_personnes = request.GET.get('nombre_personnes', 1)
    
    # Construire l'URL vers le système de réservation
    reservation_url = f"/reservations/reserver/{maison_slug}/"
    
    # Ajouter les paramètres s'ils existent
    params = []
    if date_debut:
        params.append(f"date_debut={date_debut}")
    if date_fin:
        params.append(f"date_fin={date_fin}")
    if nombre_personnes:
        params.append(f"nombre_personnes={nombre_personnes}")
    
    if params:
        reservation_url += "?" + "&".join(params)
    
    return redirect(reservation_url)


# ======== INVENTAIRE DES MEUBLES ========

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
        dernier_inventaire = maison.inventaires.first() if hasattr(maison, 'inventaires') else None
        
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


# ======== AJAX ET API ========

@require_http_methods(["GET"])
def verifier_disponibilite_maison(request, maison_slug):
    """Vérifier la disponibilité d'une maison pour des dates données"""
    
    if not RESERVATIONS_AVAILABLE:
        return JsonResponse({'error': 'Service de réservation indisponible'}, status=503)
    
    maison = get_object_or_404(Maison, slug=maison_slug)
    
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    if not date_debut or not date_fin:
        return JsonResponse({'error': 'Dates manquantes'}, status=400)
    
    try:
        from datetime import datetime
        debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
        fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
        
        disponible = Reservation.objects.verifier_disponibilite(maison, debut, fin)
        
        # Calculer le prix total
        nombre_nuits = (fin - debut).days
        prix_total = maison.prix_par_nuit * nombre_nuits
        
        return JsonResponse({
            'disponible': disponible,
            'nombre_nuits': nombre_nuits,
            'prix_par_nuit': float(maison.prix_par_nuit),
            'prix_total': float(prix_total),
            'maison_nom': maison.nom,
            'maison_ville': str(maison.ville)
        })
        
    except ValueError:
        return JsonResponse({'error': 'Format de date invalide'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def recherche_ajax(request):
    """Recherche AJAX pour l'autocomplétion"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        query = request.GET.get('q', '')
        
        if len(query) >= 2:
            user = request.user if request.user.is_authenticated else None
            
            # Recherche dans les maisons
            if MAISON_SERVICE_AVAILABLE and user:
                try:
                    maisons = MaisonService.search_maisons(query, user)[:5]
                except Exception:
                    maisons = Maison.objects.accessible_to_user(user).filter(
                        Q(nom__icontains=query) | Q(description__icontains=query)
                    )[:5]
            else:
                maisons = Maison.objects.accessible_to_user(user).filter(
                    Q(nom__icontains=query) | Q(description__icontains=query)
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



@require_http_methods(["GET"])
def api_maisons_disponibles(request):
    """API endpoint pour récupérer les maisons disponibles"""
    maisons = Maison.objects.filter(disponible=True).with_photos_and_details()
    
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


@require_http_methods(["GET"])
def api_maison_disponibilite(request, maison_id):
    """API pour vérifier la disponibilité d'une maison"""
    
    if not RESERVATIONS_AVAILABLE:
        return JsonResponse({'error': 'Service indisponible'}, status=503)
    
    try:
        maison = get_object_or_404(Maison, id=maison_id)
        
        # Vérifier si la maison est globalement disponible
        disponible_base = maison.disponible and maison.statut_occupation == 'libre'
        
        context = {
            'maison_id': maison.id,
            'nom': maison.nom,
            'disponible_base': disponible_base,
            'prix_par_nuit': float(maison.prix_par_nuit),
            'capacite_personnes': maison.capacite_personnes,
        }
        
        # Si des dates sont fournies, vérifier la disponibilité pour ces dates
        date_debut = request.GET.get('date_debut')
        date_fin = request.GET.get('date_fin')
        
        if date_debut and date_fin:
            try:
                from datetime import datetime
                debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
                fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
                
                disponible_dates = Reservation.objects.verifier_disponibilite(maison, debut, fin)
                
                context.update({
                    'disponible_dates': disponible_dates,
                    'date_debut': date_debut,
                    'date_fin': date_fin,
                    'nombre_nuits': (fin - debut).days,
                    'prix_total': float(maison.prix_par_nuit * (fin - debut).days)
                })
            except ValueError:
                context['error_dates'] = 'Format de dates invalide'
        
        return JsonResponse(context)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def ajax_maisons_par_ville(request, ville_id):
    """Retourner les maisons d'une ville spécifique en AJAX"""
    try:
        ville = get_object_or_404(Ville, id=ville_id)
        maisons = Maison.objects.filter(ville=ville, disponible=True)
        
        data = [{
            'id': m.id,
            'nom': m.nom,
            'prix': float(m.prix_par_nuit),
            'capacite': m.capacite_personnes,
            'url': m.get_absolute_url()
        } for m in maisons]
        
        return JsonResponse({'maisons': data, 'ville': ville.nom})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def ajax_categories(request):
    """Retourner toutes les catégories en AJAX"""
    categories = CategorieMaison.objects.all()
    data = [{
        'id': c.id,
        'nom': c.nom,
        'description': c.description
    } for c in categories]
    
    return JsonResponse({'categories': data})


@require_http_methods(["GET"])
def api_maison_stats(request, maison_id):
    """Statistiques d'une maison spécifique"""
    maison = get_object_or_404(Maison, id=maison_id)
    
    # Vérifier les permissions
    if not maison.can_be_managed_by(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # TODO: Calculer les vraies statistiques avec l'app reservations
    stats = {
        'reservations_total': 0,
        'revenus_total': 0,
        'taux_occupation': 0,
        'note_moyenne': maison.note_moyenne,
        'derniere_reservation': None,
        'statut_occupation': maison.statut_occupation,
        'jours_restants_location': maison.jours_restants_location,
        'nombre_meubles': maison.nombre_meubles,
        'meubles_defectueux': maison.meubles_defectueux,
    }
    
    return JsonResponse(stats)


# ======== EXPORTS ET RAPPORTS ========

@login_required
def export_maisons(request):
    """Exporter la liste des maisons en CSV"""
    user = request.user
    
    # Vérifier les permissions
    if not (hasattr(user, 'is_gestionnaire') and user.is_gestionnaire()) and \
       not (hasattr(user, 'is_super_admin') and user.is_super_admin()) and \
       not user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Récupérer les maisons selon les permissions
    maisons = Maison.objects.accessible_to_user(user)
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="maisons_export.csv"'
    
    # BOM pour Excel UTF-8
    response.write('\ufeff')
    
    writer = csv.writer(response)
    writer.writerow([
        'Numéro', 'Nom', 'Ville', 'Catégorie', 'Prix/nuit (FCFA)', 
        'Capacité', 'Chambres', 'Salles de bain', 'Superficie (m²)',
        'Statut occupation', 'Disponible', 'Featured', 'Gestionnaire',
        'Date création'
    ])
    
    for maison in maisons:
        writer.writerow([
            maison.numero,
            maison.nom,
            str(maison.ville),
            str(maison.categorie) if maison.categorie else '',
            maison.prix_par_nuit,
            maison.capacite_personnes,
            maison.nombre_chambres,
            maison.nombre_salles_bain,
            maison.superficie,
            maison.get_statut_occupation_display(),
            'Oui' if maison.disponible else 'Non',
            'Oui' if maison.featured else 'Non',
            str(maison.gestionnaire),
            maison.date_creation.strftime('%d/%m/%Y %H:%M')
        ])
    
    return response


@login_required
def rapport_gestionnaire(request):
    """Rapport détaillé pour le gestionnaire"""
    user = request.user
    
    # Vérifier les permissions
    if not (hasattr(user, 'is_gestionnaire') and user.is_gestionnaire()) and \
       not (hasattr(user, 'is_super_admin') and user.is_super_admin()) and \
       not user.is_superuser:
        messages.error(request, "Accès non autorisé.")
        return redirect('home:index')
    
    maisons = Maison.objects.accessible_to_user(user).with_photos_and_details()
    
    # Statistiques générales
    stats_generales = {
        'total_maisons': maisons.count(),
        'maisons_disponibles': maisons.filter(disponible=True).count(),
        'maisons_occupees': maisons.filter(statut_occupation='occupe').count(),
        'maisons_maintenance': maisons.filter(statut_occupation='maintenance').count(),
        'maisons_featured': maisons.filter(featured=True).count(),
        'revenus_potentiels': sum(m.prix_par_nuit for m in maisons.filter(disponible=True)),
        'prix_moyen': maisons.aggregate(Avg('prix_par_nuit'))['prix_par_nuit__avg'] or 0,
    }
    
    # Répartition par ville
    repartition_villes = maisons.values('ville__nom').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Répartition par catégorie
    repartition_categories = maisons.exclude(categorie__isnull=True).values(
        'categorie__nom'
    ).annotate(count=Count('id')).order_by('-count')
    
    # Maisons nécessitant une attention
    maisons_attention = []
    
    # Maisons en maintenance
    maisons_maintenance = maisons.filter(statut_occupation='maintenance')
    for maison in maisons_maintenance:
        maisons_attention.append({
            'maison': maison,
            'type': 'maintenance',
            'message': 'Maison en maintenance'
        })
    
    # Maisons avec meubles défectueux (si module meubles disponible)
    try:
        from meubles.models import Meuble
        maisons_meubles_defectueux = maisons.filter(meubles__etat='defectueux').distinct()
        for maison in maisons_meubles_defectueux:
            nb_defectueux = maison.meubles_defectueux
            maisons_attention.append({
                'maison': maison,
                'type': 'meubles',
                'message': f'{nb_defectueux} meuble(s) défectueux'
            })
    except ImportError:
        pass
    
    # Maisons sans photos
    maisons_sans_photos = maisons.filter(photos__isnull=True)
    for maison in maisons_sans_photos:
        maisons_attention.append({
            'maison': maison,
            'type': 'photo',
            'message': 'Aucune photo'
        })
    
    context = {
        'maisons': maisons,
        'stats_generales': stats_generales,
        'repartition_villes': repartition_villes,
        'repartition_categories': repartition_categories,
        'maisons_attention': maisons_attention,
        'user_role': getattr(user, 'role', None),
        'gestionnaire_nom': getattr(user, 'nom_complet', f"{user.first_name} {user.last_name}"),
    }
    
    return render(request, 'home/rapport_gestionnaire.html', context)


# ======== GESTION DES LOCATAIRES ET OCCUPATION ========

@login_required
@require_http_methods(["POST"])
def occuper_maison(request, slug):
    """Marquer une maison comme occupée"""
    maison = get_object_or_404(Maison, slug=slug)
    
    # Vérifier les permissions
    if not maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour modifier cette maison.")
        return redirect('home:maison_detail', slug=slug)
    
    # Récupérer les données du formulaire
    locataire_id = request.POST.get('locataire_id')
    date_fin = request.POST.get('date_fin')
    
    if not locataire_id or not date_fin:
        messages.error(request, "Locataire et date de fin requis.")
        return redirect('home:maison_detail', slug=slug)
    
    try:
        # Récupérer le locataire
        locataire = User.objects.get(id=locataire_id)
        
        # Convertir la date
        from datetime import datetime
        date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
        
        # Occuper la maison
        maison.occuper_maison(locataire, date_fin_obj)
        
        messages.success(request, f'Maison occupée par {locataire} jusqu\'au {date_fin_obj.strftime("%d/%m/%Y")}.')
        
    except User.DoesNotExist:
        messages.error(request, "Locataire introuvable.")
    except ValueError:
        messages.error(request, "Format de date invalide.")
    except Exception as e:
        messages.error(request, f"Erreur lors de l'occupation: {str(e)}")
    
    return redirect('home:maison_detail', slug=slug)


@login_required
@require_http_methods(["POST"])
def liberer_maison(request, slug):
    """Libérer une maison occupée"""
    maison = get_object_or_404(Maison, slug=slug)
    
    # Vérifier les permissions
    if not maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour modifier cette maison.")
        return redirect('home:maison_detail', slug=slug)
    
    if maison.statut_occupation == 'occupe':
        ancien_locataire = maison.locataire_actuel
        maison.liberer_maison()
        messages.success(request, f'Maison libérée. Ancien locataire: {ancien_locataire}.')
    else:
        messages.warning(request, 'Cette maison n\'est pas occupée.')
    
    return redirect('home:maison_detail', slug=slug)


# ======== UTILITAIRES ET HELPERS ========

@require_http_methods(["GET"])
def get_clients_ajax(request):
    """Récupérer la liste des clients pour les sélecteurs AJAX"""
    if not request.user.is_authenticated:
        return JsonResponse({'clients': []})
    
    # Seulement pour les gestionnaires et admins
    if not ((hasattr(request.user, 'is_gestionnaire') and request.user.is_gestionnaire()) or 
            (hasattr(request.user, 'is_super_admin') and request.user.is_super_admin()) or
            request.user.is_superuser):
        return JsonResponse({'clients': []})
    
    query = request.GET.get('q', '')
    clients = User.objects.filter(role='CLIENT') if hasattr(User, 'role') else User.objects.filter(is_staff=False)
    
    if query:
        clients = clients.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    
    clients = clients[:10]  # Limiter les résultats
    
    data = [{
        'id': client.id,
        'nom': f"{client.first_name} {client.last_name}",
        'email': client.email,
    } for client in clients]
    
    return JsonResponse({'clients': data})


def get_maison_context_data(maison, user):
    """Helper pour récupérer les données contextuelles d'une maison"""
    context = {
        'equipements': {
            'wifi': maison.wifi,
            'parking': maison.parking,
            'piscine': maison.piscine,
            'jardin': maison.jardin,
            'climatisation': maison.climatisation,
            'lave_vaisselle': maison.lave_vaisselle,
            'machine_laver': maison.machine_laver,
            'balcon': maison.balcon,
            'terrasse': maison.terrasse,
        },
        'infos_occupation': {
            'est_occupee': maison.est_occupee,
            'locataire_actuel': maison.locataire_actuel,
            'date_fin_location': maison.date_fin_location,
            'jours_restants': maison.jours_restants_location,
        },
        'permissions': {
            'can_manage': maison.can_be_managed_by(user),
            'can_reserve': user.is_authenticated and hasattr(user, 'is_client') and user.is_client(),
            'can_view_contact': user.is_authenticated and hasattr(user, 'is_client') and user.is_client(),
        }
    }
    
    return context


# ======== VUES D'ERREUR PERSONNALISÉES ========

def custom_404_view(request, exception=None):
    """Vue 404 personnalisée"""
    context = {
        'maisons_suggestions': Maison.objects.filter(
            disponible=True, featured=True
        ).with_photos_and_details()[:3]
    }
    return render(request, '404.html', context, status=404)


def custom_500_view(request):
    """Vue 500 personnalisée"""
    return render(request, '500.html', status=500)


# ======== VUES ADMIN SUPPLÉMENTAIRES ========

class VillesListView(LoginRequiredMixin, GestionnaireRequiredMixin, ListView):
    """Vue pour lister les villes"""
    model = Ville
    template_name = 'home/villes_list.html'
    context_object_name = 'villes'
    paginate_by = 20
    
    def get_queryset(self):
        return Ville.objects.annotate(
            nombre_maisons=Count('maison')
        ).order_by('nom')


class CategoriesListView(LoginRequiredMixin, GestionnaireRequiredMixin, ListView):
    """Vue pour lister les catégories"""
    model = CategorieMaison
    template_name = 'home/categories_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return CategorieMaison.objects.annotate(
            nombre_maisons=Count('maison')
        ).order_by('nom')


class UtilisateursListView(LoginRequiredMixin, ListView):
    """Vue pour lister les utilisateurs (super admins seulement)"""
    model = User
    template_name = 'home/utilisateurs_list.html'
    context_object_name = 'utilisateurs'
    paginate_by = 20
    
    def test_func(self):
        """Seuls les super admins peuvent voir cette vue"""
        user = self.request.user
        return (hasattr(user, 'is_super_admin') and user.is_super_admin()) or user.is_superuser
    
    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "Accès non autorisé.")
            return redirect('home:gestionnaire_dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return User.objects.all().order_by('date_joined')


@login_required
def export_photos(request):
    """Exporter la liste des photos en CSV"""
    user = request.user
    
    # Vérifier les permissions
    if not ((hasattr(user, 'is_gestionnaire') and user.is_gestionnaire()) or 
            (hasattr(user, 'is_super_admin') and user.is_super_admin()) or
            user.is_superuser):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Récupérer les photos selon les permissions
    if hasattr(user, 'is_super_admin') and user.is_super_admin():
        photos = PhotoMaison.objects.all()
    else:
        photos = PhotoMaison.objects.filter(maison__gestionnaire=user)
    
    photos = photos.select_related('maison').order_by('maison__nom', 'ordre')
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="photos_export.csv"'
    
    # BOM pour Excel UTF-8
    response.write('\ufeff')
    
    writer = csv.writer(response)
    writer.writerow([
        'Maison', 'Titre', 'Type', 'Principale', 'Ordre', 
        'Taille (KB)', 'Date ajout'
    ])
    
    for photo in photos:
        writer.writerow([
            photo.maison.nom,
            photo.titre,
            photo.get_type_photo_display(),
            'Oui' if photo.principale else 'Non',
            photo.ordre,
            round(photo.taille_fichier / 1024, 2) if photo.taille_fichier else 'N/A',
            photo.date_ajout.strftime('%d/%m/%Y %H:%M')
        ])
    
    return response


# ======== MAINTENANCE ET STATISTIQUES ========
@login_required
def statistiques_generales(request):
    """Vue des statistiques générales pour les gestionnaires et admins"""
    user = request.user
    
    # Vérifier les permissions
    if not ((hasattr(user, 'is_gestionnaire') and user.is_gestionnaire()) or 
            (hasattr(user, 'is_super_admin') and user.is_super_admin()) or
            user.is_superuser):
        messages.error(request, "Accès non autorisé.")
        return redirect('home:index')
    
    # Récupérer les maisons selon les permissions
    maisons = Maison.objects.accessible_to_user(user)
    
    # Statistiques de base
    stats = {
        'total_maisons': maisons.count(),
        'maisons_disponibles': maisons.filter(disponible=True).count(),
        'maisons_occupees': maisons.filter(statut_occupation='occupe').count(),
        'maisons_maintenance': maisons.filter(statut_occupation='maintenance').count(),
        'maisons_featured': maisons.filter(featured=True).count(),
        'total_photos': PhotoMaison.objects.filter(maison__in=maisons).count(),
        'prix_moyen': maisons.aggregate(Avg('prix_par_nuit'))['prix_par_nuit__avg'] or 0,
        'capacite_totale': maisons.aggregate(Sum('capacite_personnes'))['capacite_personnes__sum'] or 0,
    }
    
    # Évolution mensuelle (simulée pour l'instant)
    import datetime
    from datetime import timedelta
    
    mois_actuels = []
    for i in range(6):
        date = datetime.date.today() - timedelta(days=30*i)
        mois_actuels.append({
            'mois': date.strftime('%B %Y'),
            'nouvelles_maisons': maisons.filter(
                date_creation__year=date.year,
                date_creation__month=date.month
            ).count()
        })
    
    # Répartition par statut
    repartition_statuts = []
    for statut_code, statut_label in Maison.STATUT_OCCUPATION_CHOICES:
        count = maisons.filter(statut_occupation=statut_code).count()
        if count > 0:
            repartition_statuts.append({
                'statut': statut_label,
                'count': count,
                'pourcentage': round((count / stats['total_maisons']) * 100, 1) if stats['total_maisons'] > 0 else 0
            })
    
    # Top villes
    top_villes = maisons.values('ville__nom').annotate(
        count=Count('id'),
        revenus_potentiels=Sum('prix_par_nuit')
    ).order_by('-count')[:5]
    
    context = {
        'stats': stats,
        'mois_actuels': reversed(mois_actuels),
        'repartition_statuts': repartition_statuts,
        'top_villes': top_villes,
        'user_role': getattr(user, 'role', None),
        'reservations_available': RESERVATIONS_AVAILABLE,
    }
    
    return render(request, 'home/statistiques_generales.html', context)

@login_required
def statistiques_maison(request, slug):
    """Page de statistiques détaillées pour une maison"""
    maison = get_object_or_404(Maison, slug=slug)
    
    # Vérifier les permissions
    if not maison.can_be_managed_by(request.user):
        messages.error(request, "Vous n'avez pas les droits pour voir les statistiques de cette maison.")
        return redirect('home:maison_detail', slug=slug)
    
    # Statistiques de base
    stats = {
        'creation': maison.date_creation,
        'derniere_modification': maison.date_modification,
        'nombre_photos': maison.photos.count(),
        'photo_principale': maison.photo_principale is not None,
        'nombre_meubles': maison.nombre_meubles,
        'meubles_bon_etat': maison.meubles_bon_etat,
        'meubles_defectueux': maison.meubles_defectueux,
    }
    
    # TODO: Ajouter les statistiques de réservation quand l'app sera disponible
    
    context = {
        'maison': maison,
        'stats': stats,
    }
    
    return render(request, 'home/maison_statistiques.html', context)


class GestionnaireDashboardView(LoginRequiredMixin, GestionnaireRequiredMixin, ListView):
    model = Maison
    template_name = 'home/gestionnaire_dashboard.html'
    context_object_name = 'maisons'
    paginate_by = 5
    
    def get_queryset(self):
        return Maison.objects.accessible_to_user(self.request.user).order_by('-date_creation')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        maisons = self.get_queryset()
        context['stats'] = {
            'total_maisons': maisons.count(),
            'maisons_disponibles': maisons.filter(disponible=True).count(),
            'maisons_occupees': maisons.filter(statut_occupation='occupe').count(),
            'maisons_maintenance': maisons.filter(statut_occupation='maintenance').count(),
            'revenus_potentiels': sum(m.prix_par_nuit for m in maisons.filter(disponible=True)),
        }
        
        # Maisons nécessitant une attention
        context['maisons_attention'] = maisons.filter(
            Q(statut_occupation='maintenance') | 
            Q(meubles__etat='defectueux')
        ).distinct()[:5]
        
        context['reservations_available'] = RESERVATIONS_AVAILABLE
        
        return context


# ======== AUTRES VUES AVEC CONTEXT RESERVATIONS ========

class GestionnaireMaisonsView(LoginRequiredMixin, GestionnaireRequiredMixin, ListView):
    """Liste des maisons du gestionnaire"""
    model = Maison
    template_name = 'home/gestionnaire_maisons.html'
    context_object_name = 'maisons'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Maison.objects.accessible_to_user(self.request.user)
        
        # Filtres optionnels
        statut = self.request.GET.get('statut')
        if statut:
            queryset = queryset.filter(statut_occupation=statut)
        
        disponible = self.request.GET.get('disponible')
        if disponible == '1':
            queryset = queryset.filter(disponible=True)
        elif disponible == '0':
            queryset = queryset.filter(disponible=False)
        
        return queryset.order_by('-date_creation')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_filters'] = self.request.GET
        context['statuts'] = Maison.STATUT_OCCUPATION_CHOICES
        context['reservations_available'] = RESERVATIONS_AVAILABLE
        return context
