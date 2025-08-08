# ==========================================
# apps/comptabilite/urls.py
# ==========================================
from django.urls import path
from . import views

app_name = 'comptabilite'

urlpatterns = [
    # Vue mensuelle simple selon cahier
    path('', views.rapport_mensuel, name='rapport_mensuel'),
    path('<int:annee>/<int:mois>/', views.rapport_mensuel, name='rapport_mensuel_date'),
    
    # Détail par appartement selon cahier
    path('appartement/<int:appartement_pk>/', views.detail_appartement, name='detail_appartement'),
    
    # Ajout mouvements selon cahier (addition/soustraction simple)
    path('mouvement/ajouter/', views.ajouter_mouvement, name='ajouter_mouvement'),
    path('mouvement/<int:pk>/modifier/', views.modifier_mouvement, name='modifier_mouvement'),
    path('mouvement/<int:pk>/supprimer/', views.supprimer_mouvement, name='supprimer_mouvement'),
    path('mouvement/<int:pk>/detail/', views.detail_mouvement, name='detail_mouvement'),

    # Export simple (bonus)
    path('export/<int:annee>/<int:mois>/', views.export_rapport, name='export_rapport'),
]
