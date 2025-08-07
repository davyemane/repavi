# ==========================================
# apps/clients/urls.py
# ==========================================
from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    # Gestion clients selon cahier
    path('', views.liste_clients, name='liste'),
    path('nouveau/', views.creer_client, name='nouveau'),
    path('<int:pk>/', views.detail_client, name='detail'),
    path('<int:pk>/modifier/', views.modifier_client, name='modifier'),
    
    # Recherche selon cahier (nom ou téléphone)
    path('recherche/', views.recherche_clients, name='recherche'),
    
    # Historique des séjours selon cahier
    path('<int:pk>/historique/', views.historique_sejours, name='historique'),
]