# home/urls.py - Version complète et organisée
from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    # ======== PAGES PUBLIQUES ========
    path('', views.index, name='index'),
    path('contact/', views.contact, name='contact'),
    path('a-propos/', views.apropos, name='apropos'),
    
    # ======== MAISONS - CONSULTATION ========
    path('maisons/', views.MaisonListView.as_view(), name='maisons_list'),
    path('maison/<slug:slug>/', views.MaisonDetailView.as_view(), name='maison_detail'),
    path('maison/<slug:slug>/inventaire/', views.maison_inventaire, name='maison_inventaire'),
    
    # ======== MAISONS - GESTION (URLs manquantes) ========
    path('maisons/nouvelle/', views.MaisonCreateView.as_view(), name='maison_create'),
    path('maison/<slug:slug>/modifier/', views.MaisonUpdateView.as_view(), name='maison_update'),
    path('maison/<slug:slug>/supprimer/', views.MaisonDeleteView.as_view(), name='maison_delete'),
    path('maison/<slug:slug>/toggle-disponibilite/', views.toggle_maison_disponibilite, name='maison_toggle_disponibilite'),
    
    # ======== PHOTOS DES MAISONS ========
    path('photos/', views.PhotosListView.as_view(), name='photos_list'),
    path('maison/<slug:slug>/photos/', views.MaisonPhotosView.as_view(), name='maison_photos'),
    path('maison/<slug:slug>/photos/ajouter/', views.ajouter_photo_maison, name='maison_add_photo'),
    path('photo/<int:photo_id>/supprimer/', views.supprimer_photo_maison, name='maison_delete_photo'),
    path('photo/<int:photo_id>/principale/', views.definir_photo_principale, name='maison_set_main_photo'),
    
    # ======== DASHBOARD GESTIONNAIRE ========
    path('dashboard/', views.GestionnaireDashboardView.as_view(), name='gestionnaire_dashboard'),
    path('mes-maisons/', views.GestionnaireMaisonsView.as_view(), name='mes_maisons'),
    path('statistiques/', views.statistiques_generales, name='statistiques_generales'),
    path('maison/<slug:slug>/statistiques/', views.statistiques_maison, name='maison_statistiques'),
    
    # ======== GESTION DES LOCATAIRES ========
    path('maison/<slug:slug>/occuper/', views.occuper_maison, name='occuper_maison'),
    path('maison/<slug:slug>/liberer/', views.liberer_maison, name='liberer_maison'),
    path('ajax/clients/', views.get_clients_ajax, name='get_clients_ajax'),
    
    # ======== AJAX ET API ========
    path('recherche-ajax/', views.recherche_ajax, name='recherche_ajax'),
    path('api/maisons-disponibles/', views.api_maisons_disponibles, name='api_maisons_disponibles'),
    path('api/maison/<int:maison_id>/stats/', views.api_maison_stats, name='api_maison_stats'),
    
    # ======== FILTRES DYNAMIQUES ========
    path('ajax/maisons-par-ville/<int:ville_id>/', views.ajax_maisons_par_ville, name='ajax_maisons_par_ville'),
    path('ajax/categories/', views.ajax_categories, name='ajax_categories'),
    
    # ======== VUES ADMIN SUPPLÉMENTAIRES ========
    path('villes/', views.VillesListView.as_view(), name='villes_list'),
    path('categories/', views.CategoriesListView.as_view(), name='categories_list'),
    path('utilisateurs/', views.UtilisateursListView.as_view(), name='utilisateurs_list'),
    
    # ======== EXPORTS ET RAPPORTS ========
    path('export/maisons/', views.export_maisons, name='export_maisons'),
    path('rapport/gestionnaire/', views.rapport_gestionnaire, name='rapport_gestionnaire'),
    path('export/photos/', views.export_photos, name='export_photos'),

]