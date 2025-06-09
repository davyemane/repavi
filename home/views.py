# home/views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.generic import ListView, DetailView
from django.contrib import messages
from .models import Maison, CategorieMaison, Ville, PhotoMaison, Reservation
import json

def index(request):
    """Vue principale de la page d'accueil"""
    
    # Récupérer les maisons featured pour la page d'accueil
    maisons_featured = Maison.objects.filter(
        featured=True, 
        disponible=True
    ).select_related('ville', 'categorie').prefetch_related('photos')[:6]
    
    # Statistiques pour la section stats
    stats = {
        'total_maisons': Maison.objects.filter(disponible=True).count(),
        'total_villes': Ville.objects.count(),
        'total_reservations': Reservation.objects.filter(statut='confirmee').count(),
        'satisfaction_client': 98,  # Peut être calculé dynamiquement plus tard
    }
    
    # Catégories populaires
    categories = CategorieMaison.objects.annotate(
        nombre_maisons=Count('maison')
    ).filter(nombre_maisons__gt=0)[:4]
    
    # Villes populaires
    villes_populaires = Ville.objects.annotate(
        nombre_maisons=Count('maison')
    ).filter(nombre_maisons__gt=0).order_by('-nombre_maisons')[:6]
    
    context = {
        'maisons_featured': maisons_featured,
        'stats': stats,
        'categories': categories,
        'villes_populaires': villes_populaires,
        'page_title': 'Accueil - MaisonLoc',
        'meta_description': 'Trouvez et réservez la maison meublée parfaite pour vos vacances. Plus de 250 maisons vérifiées dans toute la France.',
    }
    
    return render(request, 'home/index.html', context)

class MaisonListView(ListView):
    """Vue liste des maisons avec filtres"""
    model = Maison
    template_name = 'home/maisons_list.html'
    context_object_name = 'maisons'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Maison.objects.filter(disponible=True).select_related(
            'ville', 'categorie'
        ).prefetch_related('photos')
        
        # Filtres de recherche
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) |
                Q(description__icontains=search) |
                Q(ville__nom__icontains=search)
            )
        
        # Filtre par ville
        ville_id = self.request.GET.get('ville')
        if ville_id:
            queryset = queryset.filter(ville_id=ville_id)
        
        # Filtre par catégorie
        categorie_id = self.request.GET.get('categorie')
        if categorie_id:
            queryset = queryset.filter(categorie_id=categorie_id)
        
        # Filtre par capacité
        capacite = self.request.GET.get('capacite')
        if capacite:
            queryset = queryset.filter(capacite_personnes__gte=capacite)
        
        # Filtre par prix
        prix_min = self.request.GET.get('prix_min')
        prix_max = self.request.GET.get('prix_max')
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['villes'] = Ville.objects.all().order_by('nom')
        context['categories'] = CategorieMaison.objects.all()
        context['current_filters'] = self.request.GET
        return context

class MaisonDetailView(DetailView):
    """Vue détail d'une maison"""
    model = Maison
    template_name = 'home/maison_detail.html'
    context_object_name = 'maison'
    slug_field = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Photos de la maison
        context['photos'] = self.object.photos.all().order_by('ordre')
        
        # Maisons similaires
        context['maisons_similaires'] = Maison.objects.filter(
            ville=self.object.ville,
            disponible=True
        ).exclude(id=self.object.id)[:3]
        
        # Disponibilités (simplifié, à adapter selon vos besoins)
        context['disponibilites'] = self.get_disponibilites()
        
        return context
    
    def get_disponibilites(self):
        """Récupère les disponibilités de la maison"""
        # Logique simplifiée - à adapter selon vos besoins
        from datetime import datetime, timedelta
        
        reservations = Reservation.objects.filter(
            maison=self.object,
            statut__in=['confirmee', 'en_attente'],
            date_fin__gte=datetime.now().date()
        ).values_list('date_debut', 'date_fin')
        
        # Retourner les dates non disponibles
        dates_non_disponibles = []
        for reservation in reservations:
            current_date = reservation[0]
            while current_date <= reservation[1]:
                dates_non_disponibles.append(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)
        
        return json.dumps(dates_non_disponibles)

def recherche_ajax(request):
    """Recherche AJAX pour l'autocomplétion"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        query = request.GET.get('q', '')
        
        if len(query) >= 2:
            # Recherche dans les maisons
            maisons = Maison.objects.filter(
                Q(nom__icontains=query) |
                Q(ville__nom__icontains=query),
                disponible=True
            )[:5]
            
            # Recherche dans les villes
            villes = Ville.objects.filter(
                nom__icontains=query
            )[:5]
            
            results = {
                'maisons': [
                    {
                        'id': m.id,
                        'nom': m.nom,
                        'ville': str(m.ville),
                        'prix': float(m.prix_par_nuit),
                        'url': m.get_absolute_url()
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
    """Page de contact"""
    if request.method == 'POST':
        # Traitement du formulaire de contact
        nom = request.POST.get('nom')
        email = request.POST.get('email')
        sujet = request.POST.get('sujet')
        message = request.POST.get('message')
        
        # Ici vous pourriez envoyer un email ou sauvegarder en base
        # send_mail(...)
        
        messages.success(request, 'Votre message a été envoyé avec succès!')
        
    return render(request, 'home/contact.html')

def apropos(request):
    """Page à propos avec statistiques"""
    stats = {
        'annee_creation': 2020,
        'maisons_disponibles': Maison.objects.filter(disponible=True).count(),
        'villes_couvertes': Ville.objects.count(),
        'clients_satisfaits': Reservation.objects.filter(statut='terminee').count() or 10000,
    }
    
    context = {
        'stats': stats,
        'page_title': 'À propos - RepAvi',
        'meta_description': 'Découvrez l\'histoire et les valeurs de RepAvi, votre partenaire de confiance pour la location de maisons d\'exception.',
    }
    
    return render(request, 'home/apropos.html', context)