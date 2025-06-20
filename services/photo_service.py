# services/photo_service.py
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from home.models import PhotoMaison
from PIL import Image


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