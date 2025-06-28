# services/maison_service.py
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.text import slugify
from home import models
from home.models import Maison, PhotoMaison
from django.core.cache import cache


class MaisonService:
    """Service pour la gestion des maisons"""
    
    @staticmethod
    def create_maison(user, data):
        """Créer une nouvelle maison"""
        if not user.can_manage_maisons():
            raise PermissionDenied("Vous n'avez pas les droits pour créer une maison")
        
        with transaction.atomic():
            # Si pas de gestionnaire spécifié, utiliser l'utilisateur connecté
            if 'gestionnaire' not in data:
                data['gestionnaire'] = user
            
            # Générer le slug
            if not data.get('slug'):
                data['slug'] = MaisonService._generate_unique_slug(data['nom'])
            
            maison = Maison.objects.create(**data)
            
            # Invalider le cache
            MaisonService._invalidate_cache()
            
            return maison
    
    @staticmethod
    def update_maison(user, maison, data):
        """Mettre à jour une maison"""
        if not maison.can_be_managed_by(user):
            raise PermissionDenied("Vous n'avez pas les droits pour modifier cette maison")
        
        with transaction.atomic():
            for key, value in data.items():
                if key != 'gestionnaire' or user.is_super_admin():
                    setattr(maison, key, value)
            
            maison.save()
            MaisonService._invalidate_cache()
            
            return maison
    
    @staticmethod
    def delete_maison(user, maison):
        """Supprimer une maison"""
        if not maison.can_be_managed_by(user):
            raise PermissionDenied("Vous n'avez pas les droits pour supprimer cette maison")
        
        with transaction.atomic():
            maison.delete()
            MaisonService._invalidate_cache()
    
    @staticmethod
    def get_maisons_for_user(user):
        """Récupérer les maisons selon les permissions utilisateur"""
        cache_key = f"maisons_user_{user.id}_{user.role}"
        maisons = cache.get(cache_key)
        
        if not maisons:
            maisons = Maison.objects.accessible_to_user(user).with_photos_and_reservations()
            cache.set(cache_key, maisons, 300)  # 5 minutes
        
        return maisons
    
    @staticmethod
    def search_maisons(query, user=None, filters=None):
        """Recherche de maisons avec filtres"""
        cache_key = f"search_{hash(query)}_{user.id if user else 'anon'}_{hash(str(filters))}"
        results = cache.get(cache_key)
        
        if not results:
            queryset = Maison.objects.accessible_to_user(user) if user else Maison.objects.available_for_clients()
            
            if query:
                queryset = queryset.filter(
                    models.Q(nom__icontains=query) |
                    models.Q(description__icontains=query) |
                    models.Q(ville__nom__icontains=query)
                )
            
            if filters:
                if filters.get('ville'):
                    queryset = queryset.filter(ville=filters['ville'])
                if filters.get('categorie'):
                    queryset = queryset.filter(categorie=filters['categorie'])
                if filters.get('prix_min'):
                    queryset = queryset.filter(prix_par_nuit__gte=filters['prix_min'])
                if filters.get('prix_max'):
                    queryset = queryset.filter(prix_par_nuit__lte=filters['prix_max'])
            
            results = queryset[:20]  # Limiter à 20 résultats
            cache.set(cache_key, results, 180)  # 3 minutes
        
        return results
    
    @staticmethod
    def _generate_unique_slug(nom):
        """Générer un slug unique"""
        base_slug = slugify(nom)
        slug = base_slug
        counter = 1
        
        while Maison.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    @staticmethod
    def _invalidate_cache():
        """Invalider les caches liés aux maisons"""
        cache.delete_many([
            key for key in cache._cache.keys() 
            if key.startswith('maisons_') or key.startswith('search_')
        ])


