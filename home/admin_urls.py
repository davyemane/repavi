# home/admin_urls.py - Version adaptée avec décorateurs de permissions
from django.urls import path
from . import admin_views

# Utilisons 'repavi_admin' comme namespace pour éviter les conflits
app_name = 'repavi_admin'

urlpatterns = [
    # Dashboard
    path('', admin_views.admin_dashboard, name='dashboard'),
    
    # Gestion des villes
    path('villes/', admin_views.admin_villes_list, name='villes_list'),
    path('villes/creer/', admin_views.admin_ville_create, name='ville_create'),
    path('villes/<int:pk>/modifier/', admin_views.admin_ville_edit, name='ville_edit'),
    path('villes/<int:pk>/supprimer/', admin_views.admin_ville_delete, name='ville_delete'),
    
    # Gestion des catégories
    path('categories/', admin_views.admin_categories_list, name='categories_list'),
    path('categories/creer/', admin_views.admin_categorie_create, name='categorie_create'),
    path('categories/<int:pk>/modifier/', admin_views.admin_categorie_edit, name='categorie_edit'),
    path('categories/<int:pk>/supprimer/', admin_views.admin_categorie_delete, name='categorie_delete'),
    
    # Gestion des maisons
    path('maisons/', admin_views.admin_maisons_list, name='maisons_list'),
    path('maisons/creer/', admin_views.admin_maison_create, name='maison_create'),
    path('maisons/<int:pk>/modifier/', admin_views.admin_maison_edit, name='maison_edit'),
    path('maisons/<int:pk>/supprimer/', admin_views.admin_maison_delete, name='maison_delete'),
    
    # Gestion des photos
    path('photos/', admin_views.admin_photos_list, name='photos_list'),
    path('photos/ajouter/', admin_views.admin_photo_create, name='photo_create'),
    path('photos/<int:pk>/modifier/', admin_views.admin_photo_edit, name='photo_edit'),
    path('photos/<int:pk>/supprimer/', admin_views.admin_photo_delete, name='photo_delete'),
    
    # Gestion des réservations
    path('reservations/', admin_views.admin_reservations_list, name='reservations_list'),
    path('reservations/creer/', admin_views.admin_reservation_create, name='reservation_create'),
    path('reservations/<int:pk>/modifier/', admin_views.admin_reservation_edit, name='reservation_edit'),
    path('reservations/<int:pk>/supprimer/', admin_views.admin_reservation_delete, name='reservation_delete'),
]