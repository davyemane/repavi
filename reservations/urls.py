# reservations/urls.py - URLs pour les réservations avec fonctionnalités admin

from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    # ======== PAGES PUBLIQUES ========
    path('recherche/', views.recherche_disponibilite, name='recherche_disponibilite'),
    
    # ======== DASHBOARD ET GESTION ========
    path('', views.dashboard_admin_reservations, name='dashboard'),
    path('dashboard/', views.reservations_dashboard, name='dashboard_alt'),
    path('tableau-bord/', views.tableau_bord_reservations, name='tableau_bord_gestionnaire'),
    
    # ======== DASHBOARD ADMIN ========
    path('', views.dashboard_admin_reservations, name='dashboard_admin'),
    path('admin-historique/', views.historique_actions_admin, name='historique_actions_admin'),
    
    # ======== RÉSERVATIONS UTILISATEUR ========
    path('mes-reservations/', views.mes_reservations, name='mes_reservations'),
    path('reserver/<slug:maison_slug>/', views.reserver_maison, name='reserver_maison'),
    
    # ======== DÉTAILS ET GESTION D'UNE RÉSERVATION ========
    path('reservation/<str:numero>/', views.detail_reservation, name='detail'),
    path('reservation/<str:numero>/modifier/', views.modifier_reservation, name='modifier'),
    path('reservation/<str:numero>/annuler/', views.annuler_reservation, name='annuler'),
    path('reservation/<str:numero>/gerer/', views.gerer_reservation, name='gerer'),
    
    # ======== GESTION ADMINISTRATEUR ========
    path('reservation/<str:numero>/gerer-admin/', views.gerer_reservation_admin, name='gerer_admin'),
    path('reservation/<str:numero>/validation-rapide/', views.validation_rapide_admin, name='validation_rapide_admin'),
    
    # ======== ACTIONS RAPIDES GESTIONNAIRE ========
    path('reservation/<str:numero>/valider/', views.valider_reservation, name='valider'),
    path('reservation/<str:numero>/terminer/', views.terminer_reservation, name='terminer'),
    
    # ======== PAIEMENTS ========
    path('reservation/<str:numero>/paiements/', views.paiements_reservation, name='paiements'),
    path('reservation/<str:numero>/paiements/ajouter/', views.ajouter_paiement, name='ajouter_paiement'),
    path('paiements/dashboard/', views.dashboard_paiements, name='dashboard_paiements'),
    path('paiements/<int:paiement_id>/valider/', views.valider_paiement, name='valider_paiement'),
    
    # ======== ÉVALUATIONS ========
    path('reservation/<str:numero>/evaluer/', views.evaluer_reservation, name='evaluer'),
    path('reservation/<str:numero>/repondre-evaluation/', views.repondre_evaluation, name='repondre_evaluation'),
    
    # ======== CALENDRIER ET DISPONIBILITÉS ========
    path('calendrier/', views.calendrier_reservations, name='calendrier'),
    path('maison/<int:maison_id>/disponibilites/', views.gerer_disponibilites, name='gerer_disponibilites'),
    
    # ======== AJAX ========
    path('ajax/verifier-disponibilite/', views.verifier_disponibilite_ajax, name='verifier_disponibilite_ajax'),
    path('ajax/modifier-disponibilite/', views.modifier_disponibilite_ajax, name='modifier_disponibilite_ajax'),
    path('ajax/calculer-prix/', views.calculer_prix_ajax, name='calculer_prix_ajax'),
    
    # ======== EXPORT ========
    path('export/', views.exporter_reservations, name='exporter_reservations'),
]