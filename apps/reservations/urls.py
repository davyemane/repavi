# ==========================================
# apps/reservations/urls.py
# ==========================================
from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    # Calendrier et planning selon cahier
    path('', views.calendrier_reservations, name='calendrier'),
    path('liste/', views.liste_reservations, name='liste'),
    
    # Création réservation (5 étapes selon cahier)
    path('nouvelle/', views.creer_reservation, name='nouvelle'),
    path('<int:pk>/', views.detail_reservation, name='detail'),
    path('<int:pk>/modifier/', views.modifier_reservation, name='modifier'),
    path('<int:pk>/annuler/', views.annuler_reservation, name='annuler'),
    
    # Vérification disponibilité selon cahier (AJAX)
    path('api/disponibilite/', views.verifier_disponibilite, name='verifier_disponibilite'),
    
    # Arrivées et départs du jour
    path('arrivees-jour/', views.arrivees_du_jour, name='arrivees_jour'),
    path('departs-jour/', views.departs_du_jour, name='departs_jour'),
]