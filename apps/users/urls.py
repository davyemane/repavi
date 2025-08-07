# ==========================================
# apps/users/urls.py
# ==========================================
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Dashboard principal (requis par le cahier des charges)
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Profil utilisateur
    path('profil/', views.profil_utilisateur, name='profil'),
    
    # Gestion utilisateurs (Super Admin uniquement selon cahier)
    path('gestionnaires/', views.ListeGestionnairesView.as_view(), name='liste_gestionnaires'),
    path('gestionnaires/nouveau/', views.creer_gestionnaire, name='creer_gestionnaire'),
    path('gestionnaires/<int:pk>/modifier/', views.modifier_gestionnaire, name='modifier_gestionnaire'),
    path('gestionnaires/<int:pk>/desactiver/', views.desactiver_gestionnaire, name='desactiver_gestionnaire'),
    path('gestionnaires/<int:pk>/reactiver/', views.reactiver_gestionnaire, name='reactiver_gestionnaire'),
    
    # Historique activités (requis par le cahier des charges)
    path('historique/', views.historique_activites, name='historique'),
]