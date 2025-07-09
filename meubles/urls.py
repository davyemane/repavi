from django.urls import path
from . import views

app_name = 'meubles'

urlpatterns = [
    # Dashboard
    path('', views.meubles_dashboard, name='dashboard'),
    
    # Meubles CRUD
    path('meubles/', views.meubles_list, name='meubles_list'),
    path('meubles/nouveau/', views.meuble_create, name='meuble_create'),
    path('meubles/<int:pk>/', views.meuble_detail, name='meuble_detail'),
    path('meubles/<int:pk>/modifier/', views.meuble_edit, name='meuble_edit'),
    path('meubles/<int:pk>/supprimer/', views.meuble_delete, name='meuble_delete'),
    
    # Actions rapides sur meubles
    path('meubles/<int:pk>/changer-etat/', views.meuble_changer_etat, name='meuble_changer_etat'),
    path('meubles/<int:pk>/marquer-verifie/', views.meuble_marquer_verifie, name='meuble_marquer_verifie'),
    
    # Types de meubles
    path('types/', views.types_meubles_list, name='types_list'),
    path('types/nouveau/', views.type_meuble_create, name='type_create'),
    path('types/<int:pk>/modifier/', views.type_meuble_edit, name='type_edit'),
    path('types/<int:pk>/supprimer/', views.type_meuble_delete, name='type_delete'),
    
    # Photos
    path('meubles/<int:meuble_pk>/photos/ajouter/', views.meuble_add_photo, name='meuble_add_photo'),
    
    # Import
    path('import/', views.meuble_import, name='meuble_import'),
    
    # Inventaires
    path('inventaires/', views.inventaires_list, name='inventaires_list'),
    path('inventaires/nouveau/', views.inventaire_create, name='inventaire_create'),
    path('inventaires/<int:pk>/', views.inventaire_detail, name='inventaire_detail'),
    
    # === RAPPORTS ET EXPORTS ===
    
    # Génération de rapports
    path('rapports/', views.generer_rapport, name='generer_rapport'),
    
    # Exports spécialisés avec paramètres (à placer AVANT le pattern générique)
    path('export/inventaire/pdf/', 
         views.export_rapport_rapide, 
         {'type_rapport': 'inventaire'}, 
         name='export_inventaire_pdf'),
    path('export/defectueux/excel/', 
         views.export_rapport_rapide, 
         {'type_rapport': 'defectueux'}, 
         name='export_defectueux_excel'),
    path('export/verification/csv/', 
         views.export_rapport_rapide, 
         {'type_rapport': 'verification'}, 
         name='export_verification_csv'),
    
    # Exports génériques
    path('export/csv/', views.export_meubles_csv, name='export_csv'),
    path('export/rapide/<str:type_rapport>/', views.export_rapport_rapide, name='export_rapide'),
    
    # Aperçu AJAX
    path('rapports/preview/', views.preview_rapport_ajax, name='preview_rapport_ajax'),
    
    # Intégration avec maisons
    path('maisons/<int:maison_id>/meubles/', views.maison_meubles_list, name='maison_meubles'),
    
    # API AJAX
    path('api/meubles/maison/<int:maison_id>/', views.api_meubles_maison, name='api_meubles_maison'),
    path('api/meuble/<int:pk>/stats/', views.api_meuble_stats, name='api_meuble_stats'),
]