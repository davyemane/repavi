# ==========================================
# apps/facturation/urls.py
# ==========================================
from django.urls import path
from . import views

app_name = 'facturation'

urlpatterns = [
    # Liste factures
    path('', views.liste_factures, name='liste'),
    
    # Génération automatique selon cahier
    path('generer/', views.generer_facture, name='generer'),
    path('reservation/<int:reservation_pk>/generer/', views.generer_facture_reservation, name='generer_reservation'),
    
    # Téléchargement PDF selon cahier
    path('<int:pk>/pdf/', views.telecharger_pdf, name='pdf'),
    path('<int:pk>/apercu/', views.apercu_facture, name='apercu'),
    
    # Gestion
    path('<int:pk>/regenerer/', views.regenerer_facture, name='regenerer'),
]
