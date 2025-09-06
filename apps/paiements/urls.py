# ==========================================
# apps/paiements/urls.py - URLs des paiements
# ==========================================
from django.urls import path
from . import views

app_name = 'paiements'

urlpatterns = [
    # Échéancier selon cahier (paiements par tranches SIMPLIFIÉ)
    path('', views.echeancier_paiements, name='echeancier'),
    path('retards/', views.paiements_en_retard, name='retards'),
    
    # Saisie paiements selon cahier
    path('<int:pk>/saisir/', views.saisir_paiement, name='saisir'),
    path('<int:pk>/modifier/', views.modifier_paiement, name='modifier'),
    
    # Génération automatique échéancier
    path('reservation/<int:reservation_pk>/generer/', views.generer_echeancier, name='generer_echeancier'),
]