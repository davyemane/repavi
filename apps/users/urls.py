# ==========================================
# apps/users/urls.py
# ==========================================
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Dashboard principal (requis par le cahier des charges)
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/receptionniste/', views.DashboardReceptionnisteView.as_view(), name='dashboard_receptionniste'),

    # Profil utilisateur
    path('profil/', views.profil_utilisateur, name='profil'),

    # Gestion utilisateurs (Super Admin uniquement selon cahier)
    path('gestionnaires/', views.ListeGestionnairesView.as_view(), name='liste_gestionnaires'),
    path('gestionnaires/nouveau/', views.creer_gestionnaire, name='creer_gestionnaire'),
    path('gestionnaires/<int:pk>/modifier/', views.modifier_gestionnaire, name='modifier_gestionnaire'),
    path('gestionnaires/<int:pk>/desactiver/', views.desactiver_gestionnaire, name='desactiver_gestionnaire'),
    path('gestionnaires/<int:pk>/reactiver/', views.reactiver_gestionnaire, name='reactiver_gestionnaire'),

    # Gestion réceptionnistes (Super Admin uniquement)
    path('receptionistes/', views.liste_receptionistes, name='liste_receptionistes'),
    path('receptionistes/nouveau/', views.creer_receptionniste, name='creer_receptionniste'),
    path('receptionistes/<int:pk>/modifier/', views.modifier_receptionniste, name='modifier_receptionniste'),
    path('receptionistes/<int:pk>/desactiver/', views.desactiver_receptionniste, name='desactiver_receptionniste'),
    path('receptionistes/<int:pk>/reactiver/', views.reactiver_receptionniste, name='reactiver_receptionniste'),

    # Historique activités (requis par le cahier des charges)
    path('historique/', views.historique_activites, name='historique'),

    path('audit/journal/', views.journal_actions, name='journal_actions'),
    path('audit/stats/', views.statistiques_audit, name='statistiques_audit'),

]