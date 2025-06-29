# home/urls.py - URLs avec intégration réservations
from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    # Pages principales
    path('', views.index, name='index'),
    path('contact/', views.contact, name='contact'),
    path('apropos/', views.apropos, name='apropos'),
    
    # Maisons - consultation publique
    path('maisons/', views.MaisonListView.as_view(), name='maisons_list'),
    
    # URLs spéciales pour les réservations (AVANT le pattern avec slug)
    path('maisons/reservation/', views.maisons_disponibles_reservation, name='maisons_reservation'),
    
    # Maisons - gestion (gestionnaires) - URLs spécifiques AVANT le pattern avec slug
    path('gestion/', views.GestionnaireDashboardView.as_view(), name='gestionnaire_dashboard'),
    path('gestion/maisons/', views.GestionnaireMaisonsView.as_view(), name='mes_maisons'),
    path('gestion/maisons/nouvelle/', views.MaisonCreateView.as_view(), name='maison_create'),
    path('gestion/statistiques/', views.statistiques_generales, name='statistiques_generales'),
    path('gestion/photos/', views.PhotosListView.as_view(), name='photos_list'),
    path('gestion/export/maisons/', views.export_maisons, name='export_maisons'),
    path('gestion/export/photos/', views.export_photos, name='export_photos'),
    path('gestion/rapports/', views.rapport_gestionnaire, name='rapport_gestionnaire'),
    
    # APIs et AJAX - URLs spécifiques
    path('api/recherche/', views.recherche_ajax, name='recherche_ajax'),
    path('api/maisons/disponibles/', views.api_maisons_disponibles, name='api_maisons_disponibles'),
    path('api/maisons/ville/<int:ville_id>/', views.ajax_maisons_par_ville, name='ajax_maisons_par_ville'),
    path('api/categories/', views.ajax_categories, name='ajax_categories'),
    path('api/maison/<int:maison_id>/disponibilite/', views.api_maison_disponibilite, name='api_maison_disponibilite'),
    path('api/clients/', views.get_clients_ajax, name='get_clients_ajax'),
    
    # Vues admin supplémentaires - URLs spécifiques
    path('admin/villes/', views.VillesListView.as_view(), name='villes_list'),
    path('admin/categories/', views.CategoriesListView.as_view(), name='categories_list'),
    path('admin/utilisateurs/', views.UtilisateursListView.as_view(), name='utilisateurs_list'),
    
    # URLs avec slug pour maisons spécifiques (APRÈS toutes les URLs spécifiques)
    path('maisons/<slug:slug>/', views.MaisonDetailView.as_view(), name='maison_detail'),
    path('maisons/<slug:maison_slug>/reserver/', views.initier_reservation, name='initier_reservation'),
    path('maisons/<slug:maison_slug>/disponibilite/', views.verifier_disponibilite_maison, name='verifier_disponibilite'),
    
    # Gestion maisons avec slug (APRÈS les URLs spécifiques)
    path('gestion/maisons/<slug:slug>/modifier/', views.MaisonUpdateView.as_view(), name='maison_update'),
    path('gestion/maisons/<slug:slug>/supprimer/', views.MaisonDeleteView.as_view(), name='maison_delete'),
    path('gestion/maisons/<slug:slug>/toggle-disponibilite/', views.toggle_maison_disponibilite, name='toggle_maison_disponibilite'),
    path('gestion/maisons/<slug:slug>/photos/', views.MaisonPhotosView.as_view(), name='maison_photos'),
    path('gestion/maisons/<slug:slug>/photos/ajouter/', views.ajouter_photo_maison, name='ajouter_photo_maison'),
    path('gestion/maisons/<slug:slug>/occuper/', views.occuper_maison, name='occuper_maison'),
    path('gestion/maisons/<slug:slug>/liberer/', views.liberer_maison, name='liberer_maison'),
    path('gestion/maisons/<slug:slug>/inventaire/', views.maison_inventaire, name='maison_inventaire'),
    path('gestion/maisons/<slug:slug>/statistiques/', views.statistiques_maison, name='statistiques_maison'),
    
    # Photos avec ID (pas de conflit possible)
    path('gestion/photos/<int:photo_id>/supprimer/', views.supprimer_photo_maison, name='supprimer_photo_maison'),
    path('gestion/photos/<int:photo_id>/principale/', views.definir_photo_principale, name='definir_photo_principale'),
]