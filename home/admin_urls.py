# repavi_admin/urls.py ou home/urls.py (selon votre structure)

from django.urls import path
from . import admin_views  # Ajustez l'import selon votre structure

app_name = 'repavi_admin'

urlpatterns = [
    # Dashboard
    path('', admin_views.admin_dashboard, name='dashboard'),
    
    # ========== GESTION DES UTILISATEURS ==========
    path('users/', admin_views.admin_users_list, name='admin_users_list'),
    path('users/create-client/', admin_views.admin_create_client, name='admin_create_client'),
    path('users/create-gestionnaire/', admin_views.admin_create_gestionnaire, name='admin_create_gestionnaire'),
    path('users/<int:user_id>/change-role/', admin_views.change_user_role_view, name='change_user_role_view'),
    path('users/<int:user_id>/toggle-status/', admin_views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/delete/', admin_views.delete_user, name='delete_user'),
    
    # ========== GESTION DES VILLES ==========
    path('villes/', admin_views.admin_villes_list, name='villes_list'),
    path('villes/create/', admin_views.admin_ville_create, name='ville_create'),
    path('villes/<int:pk>/edit/', admin_views.admin_ville_edit, name='ville_edit'),
    path('villes/<int:pk>/delete/', admin_views.admin_ville_delete, name='ville_delete'),
    
    # ========== GESTION DES CATÉGORIES ==========
    path('categories/', admin_views.admin_categories_list, name='categories_list'),
    path('categories/create/', admin_views.admin_categorie_create, name='categorie_create'),
    path('categories/<int:pk>/edit/', admin_views.admin_categorie_edit, name='categorie_edit'),
    path('categories/<int:pk>/delete/', admin_views.admin_categorie_delete, name='categorie_delete'),
    
    # ========== GESTION DES MAISONS ==========
    path('maisons/', admin_views.admin_maisons_list, name='maisons_list'),
    path('maisons/create/', admin_views.admin_maison_create, name='maison_create'),
    path('maisons/<int:pk>/', admin_views.admin_maison_detail, name='maison_detail'),
    path('maisons/<int:pk>/edit/', admin_views.admin_maison_edit, name='maison_edit'),
    path('maisons/<int:pk>/delete/', admin_views.admin_maison_delete, name='maison_delete'),
    path('maisons/<int:pk>/change-status/', admin_views.admin_maison_change_status, name='maison_change_status'),
    
    # ========== GESTION DES PHOTOS ==========
    path('photos/', admin_views.admin_photos_list, name='photos_list'),
    path('photos/create/', admin_views.admin_photo_create, name='photo_create'),
    path('photos/<int:pk>/edit/', admin_views.admin_photo_edit, name='photo_edit'),
    path('photos/<int:pk>/delete/', admin_views.admin_photo_delete, name='photo_delete'),
    path('photos/<int:pk>/set-main/', admin_views.admin_photo_set_main, name='photo_set_main'),
    
    # ========== STATISTIQUES ==========
    path('statistiques/', admin_views.admin_statistiques, name='statistiques'),
    
    # ========== API ENDPOINTS ==========
    path('api/maisons/search/', admin_views.api_maisons_search, name='api_maisons_search'),
    path('api/dashboard/stats/', admin_views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/activities/', admin_views.api_recent_activities, name='api_recent_activities'),
]

# Si vous avez le module reservations, ajoutez ces URLs conditionnellement
try:
    from reservations.models import Reservation
    urlpatterns += [
        # ========== GESTION DES RÉSERVATIONS ==========
        path('reservations/', admin_views.admin_reservations_list, name='admin_reservations_list'),
        path('reservations/create/', admin_views.admin_reservation_create, name='admin_reservation_create'),
        path('reservations/<int:pk>/edit/', admin_views.admin_reservation_edit, name='admin_reservation_edit'),
        path('reservations/<int:pk>/delete/', admin_views.admin_reservation_delete, name='admin_reservation_delete'),
        
        # ========== GESTION DES TYPES DE PAIEMENT ==========
        path('types-paiement/', admin_views.admin_types_paiement_list, name='admin_types_paiement_list'),
        path('types-paiement/create/', admin_views.admin_type_paiement_create, name='admin_type_paiement_create'),
        path('types-paiement/<int:pk>/edit/', admin_views.admin_type_paiement_edit, name='admin_type_paiement_edit'),
        path('types-paiement/<int:pk>/delete/', admin_views.admin_type_paiement_delete, name='admin_type_paiement_delete'),
    ]
except ImportError:
    pass