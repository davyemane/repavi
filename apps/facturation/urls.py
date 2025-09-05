# ==========================================
# apps/facturation/urls.py
# ==========================================
from django.urls import path
from . import views

app_name = 'facturation'

urlpatterns = [
    # Dashboard de facturation
    path('', views.dashboard_facturation, name='dashboard'),
    
    # Gestion des factures
    path('liste/', views.liste_factures, name='liste'),
    path('<int:pk>/', views.detail_facture, name='detail'),
    path('<int:pk>/modifier/', views.modifier_facture, name='modifier'),
    
    # Génération de factures
    path('reservation/<int:reservation_pk>/generer/', views.generer_facture_reservation, name='generer_reservation'),
    
    # Export PDF
    path('<int:pk>/pdf/', views.facture_pdf, name='pdf'),
    path('<int:pk>/preview/', views.facture_preview, name='preview'),
    
    # Actions sur factures
    path('<int:pk>/marquer-payee/', views.marquer_payee, name='marquer_payee'),
    path('<int:pk>/annuler/', views.annuler_facture, name='annuler'),
    
    # Paramètres
    path('parametres/', views.parametres_facturation, name='parametres'),
]