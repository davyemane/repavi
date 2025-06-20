# services/maison_service.py
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.text import slugify
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


# services/photo_service.py
from django.core.files.base import ContentFile
from PIL import Image
import io


class PhotoService:
    """Service pour la gestion des photos"""
    
    @staticmethod
    def upload_photo(user, maison, photo_data, titre="", principale=False, ordre=0):
        """Upload une photo avec validation des permissions"""
        if not maison.can_be_managed_by(user):
            raise PermissionDenied("Vous n'avez pas les droits pour ajouter des photos à cette maison")
        
        # Vérifier le nombre maximum de photos
        if maison.photos.count() >= 10:
            raise ValidationError("Nombre maximum de photos atteint (10)")
        
        with transaction.atomic():
            # Si principale=True, désactiver les autres photos principales
            if principale:
                maison.photos.update(principale=False)
            
            # Créer la photo
            photo = PhotoMaison.objects.create(
                maison=maison,
                image=photo_data,
                titre=titre,
                principale=principale,
                ordre=ordre or maison.photos.count()
            )
            
            # Optimiser l'image
            PhotoService._optimize_image(photo)
            
            return photo
    
    @staticmethod
    def update_photo(user, photo, data):
        """Mettre à jour une photo"""
        if not photo.maison.can_be_managed_by(user):
            raise PermissionDenied("Vous n'avez pas les droits pour modifier cette photo")
        
        with transaction.atomic():
            if data.get('principale') and not photo.principale:
                photo.maison.photos.update(principale=False)
            
            for key, value in data.items():
                setattr(photo, key, value)
            
            photo.save()
            return photo
    
    @staticmethod
    def delete_photo(user, photo):
        """Supprimer une photo"""
        if not photo.maison.can_be_managed_by(user):
            raise PermissionDenied("Vous n'avez pas les droits pour supprimer cette photo")
        
        photo.delete()
    
    @staticmethod
    def _optimize_image(photo):
        """Optimiser une image (compression, redimensionnement)"""
        if not photo.image:
            return
        
        try:
            image = Image.open(photo.image.path)
            
            # Redimensionnement si nécessaire
            if image.width > 1200 or image.height > 800:
                image.thumbnail((1200, 800), Image.LANCZOS)
                
                # Sauvegarder avec compression
                image.save(photo.image.path, optimize=True, quality=85)
        except Exception:
            pass  # Ignorer les erreurs d'optimisation


# services/reservation_service.py
from django.utils import timezone
from datetime import timedelta
from home.models import Reservation


class ReservationService:
    """Service pour la gestion des réservations"""
    
    @staticmethod
    def create_reservation(client, maison, data):
        """Créer une nouvelle réservation"""
        if not client.is_client():
            raise PermissionDenied("Seuls les clients peuvent faire des réservations")
        
        # Vérifier la disponibilité
        if not ReservationService.is_available(maison, data['date_debut'], data['date_fin']):
            raise ValidationError("Ces dates ne sont pas disponibles")
        
        # Calculer le prix total
        duree = (data['date_fin'] - data['date_debut']).days
        prix_total = duree * maison.prix_par_nuit
        
        with transaction.atomic():
            reservation = Reservation.objects.create(
                maison=maison,
                client=client,
                date_debut=data['date_debut'],
                date_fin=data['date_fin'],
                nombre_personnes=data['nombre_personnes'],
                prix_total=prix_total,
                telephone=data.get('telephone', client.telephone),
                message=data.get('message', ''),
                statut='en_attente'
            )
            
            # TODO: Envoyer notification au gestionnaire
            # NotificationService.notify_new_reservation(reservation)
            
            return reservation
    
    @staticmethod
    def update_reservation_status(user, reservation, nouveau_statut):
        """Mettre à jour le statut d'une réservation"""
        if not reservation.can_be_managed_by(user):
            raise PermissionDenied("Vous n'avez pas les droits pour modifier cette réservation")
        
        old_status = reservation.statut
        reservation.statut = nouveau_statut
        reservation.save()
        
        # TODO: Notifications selon le changement de statut
        # NotificationService.notify_status_change(reservation, old_status, nouveau_statut)
        
        return reservation
    
    @staticmethod
    def is_available(maison, date_debut, date_fin):
        """Vérifier la disponibilité d'une maison"""
        if not maison.disponible:
            return False
        
        # Vérifier les conflits avec d'autres réservations
        conflicting_reservations = Reservation.objects.filter(
            maison=maison,
            statut__in=['confirmee', 'en_attente'],
            date_debut__lt=date_fin,
            date_fin__gt=date_debut
        )
        
        return not conflicting_reservations.exists()
    
    @staticmethod
    def get_reservations_for_user(user):
        """Récupérer les réservations selon le rôle utilisateur"""
        if user.is_client():
            return Reservation.objects.filter(client=user).select_related('maison')
        elif user.is_gestionnaire():
            return Reservation.objects.filter(maison__gestionnaire=user).select_related('maison', 'client')
        elif user.is_super_admin():
            return Reservation.objects.all().select_related('maison', 'client')
        else:
            return Reservation.objects.none()
    
    @staticmethod
    def get_calendar_data(maison, year=None, month=None):
        """Récupérer les données du calendrier pour une maison"""
        if not year:
            year = timezone.now().year
        if not month:
            month = timezone.now().month
        
        # Récupérer les réservations du mois
        start_date = timezone.datetime(year, month, 1).date()
        if month == 12:
            end_date = timezone.datetime(year + 1, 1, 1).date()
        else:
            end_date = timezone.datetime(year, month + 1, 1).date()
        
        reservations = Reservation.objects.filter(
            maison=maison,
            statut__in=['confirmee', 'en_attente'],
            date_debut__lt=end_date,
            date_fin__gt=start_date
        )
        
        # Formater pour le calendrier frontend
        calendar_data = []
        for reservation in reservations:
            calendar_data.append({
                'start': reservation.date_debut.isoformat(),
                'end': reservation.date_fin.isoformat(),
                'title': f"Réservé - {reservation.client.first_name}",
                'status': reservation.statut,
                'id': reservation.id
            })
        
        return calendar_data


# services/statistics_service.py
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta


class StatisticsService:
    """Service pour les statistiques"""
    
    @staticmethod
    def get_dashboard_stats(user):
        """Récupérer les statistiques pour le dashboard"""
        if user.is_gestionnaire():
            return StatisticsService._get_gestionnaire_stats(user)
        elif user.is_super_admin():
            return StatisticsService._get_super_admin_stats()
        else:
            return {}
    
    @staticmethod
    def _get_gestionnaire_stats(gestionnaire):
        """Statistiques pour un gestionnaire"""
        today = timezone.now().date()
        start_month = today.replace(day=1)
        start_year = today.replace(month=1, day=1)
        
        maisons = Maison.objects.filter(gestionnaire=gestionnaire)
        reservations = Reservation.objects.filter(maison__gestionnaire=gestionnaire)
        
        return {
            'maisons_count': maisons.count(),
            'maisons_disponibles': maisons.filter(disponible=True).count(),
            'reservations_mois': reservations.filter(
                date_creation__gte=start_month,
                statut='confirmee'
            ).count(),
            'chiffre_affaires_mois': reservations.filter(
                date_creation__gte=start_month,
                statut='confirmee'
            ).aggregate(total=Sum('prix_total'))['total'] or 0,
            'chiffre_affaires_annee': reservations.filter(
                date_creation__gte=start_year,
                statut='confirmee'
            ).aggregate(total=Sum('prix_total'))['total'] or 0,
            'reservations_en_attente': reservations.filter(statut='en_attente').count(),
            'taux_occupation': StatisticsService._calculate_occupation_rate(maisons, today.month),
        }
    
    @staticmethod
    def _get_super_admin_stats():
        """Statistiques globales pour super admin"""
        today = timezone.now().date()
        start_month = today.replace(day=1)
        
        return {
            'total_utilisateurs': User.objects.count(),
            'total_clients': User.objects.filter(role='CLIENT').count(),
            'total_gestionnaires': User.objects.filter(role='GESTIONNAIRE').count(),
            'total_maisons': Maison.objects.count(),
            'maisons_actives': Maison.objects.filter(disponible=True).count(),
            'reservations_mois': Reservation.objects.filter(
                date_creation__gte=start_month
            ).count(),
            'chiffre_affaires_mois': Reservation.objects.filter(
                date_creation__gte=start_month,
                statut='confirmee'
            ).aggregate(total=Sum('prix_total'))['total'] or 0,
        }
    
    @staticmethod
    def _calculate_occupation_rate(maisons, month):
        """Calculer le taux d'occupation"""
        if not maisons.exists():
            return 0
        
        # Logique simplifiée - à améliorer selon les besoins
        total_days = 30  # Approximation
        reserved_days = Reservation.objects.filter(
            maison__in=maisons,
            statut='confirmee',
            date_debut__month=month
        ).aggregate(
            total=Sum('duree_sejour')
        )['total'] or 0
        
        max_possible_days = total_days * maisons.count()
        return (reserved_days / max_possible_days * 100) if max_possible_days > 0 else 0