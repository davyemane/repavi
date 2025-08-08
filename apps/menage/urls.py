# ==========================================
# apps/menage/urls.py
# ==========================================
from django.urls import path
from . import views

app_name = 'menage'

urlpatterns = [
    # Planning ménage basique selon cahier
    path('', views.planning_menage, name='planning'),
    path('urgentes/', views.taches_urgentes, name='urgentes'),
    
    # Check-list simple selon cahier
    path('tache/<int:pk>/checklist/', views.checklist_menage, name='checklist'),
    path('tache/<int:pk>/terminer/', views.terminer_tache, name='terminer'),
    #planning ménage basique selon cahier
    
    # Création automatique après départ
    path('generer-apres-depart/<int:reservation_pk>/', views.generer_tache_apres_depart, name='generer_apres_depart'),
    
    # Historique
    path('historique/', views.historique_menage, name='historique'),
    path('programmer/<int:appartement_pk>/', views.programmer_menage, name='programmer'),
]