# reservations/urls.py - Configuration des URLs pour les réservations

from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    # ======== URLS PUBLIQUES ========
    path('recherche/', views.recherche_disponibilite, name='recherche_disponibilite'),
    path('reserver/<slug:maison_slug>/', views.reserver_maison, name='reserver_maison'),
    
    # ======== URLS UTILISATEUR CONNECTÉ ========
    path('mes-reservations/', views.mes_reservations, name='mes_reservations'),
    path('detail/<str:numero>/', views.detail_reservation, name='detail'),
    path('modifier/<str:numero>/', views.modifier_reservation, name='modifier'),
    path('annuler/<str:numero>/', views.annuler_reservation, name='annuler'),
    
    # ======== URLS ÉVALUATIONS ========
    path('evaluer/<str:numero>/', views.evaluer_reservation, name='evaluer'),
    path('repondre-evaluation/<str:numero>/', views.repondre_evaluation, name='repondre_evaluation'),
    
    # ======== URLS PAIEMENTS ========
    path('paiements/<str:numero>/', views.paiements_reservation, name='paiements'),
    path('ajouter-paiement/<str:numero>/', views.ajouter_paiement, name='ajouter_paiement'),
    
    # ======== URLS GESTIONNAIRE ========
    path('dashboard/', views.tableau_bord_reservations, name='dashboard_gestionnaire'),
    path('gerer/<str:numero>/', views.gerer_reservation, name='gerer'),
    path('calendrier/', views.calendrier_reservations, name='calendrier'),
    path('disponibilites/<int:maison_id>/', views.gerer_disponibilites, name='gerer_disponibilites'),
    
    # ======== URLS EXPORT ========
    path('export/', views.exporter_reservations, name='export'),
    
    # ======== URLS AJAX ========
    path('ajax/verifier-disponibilite/', views.verifier_disponibilite_ajax, name='verifier_disponibilite_ajax'),
    path('ajax/modifier-disponibilite/', views.modifier_disponibilite_ajax, name='modifier_disponibilite_ajax'),
    path('ajax/calculer-prix/', views.calculer_prix_ajax, name='calculer_prix_ajax'),
]