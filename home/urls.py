# home/urls.py - Version adaptée
from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    # Pages publiques
    path('', views.index, name='index'),
    path('maisons/', views.MaisonListView.as_view(), name='maisons_list'),
    path('maison/<slug:slug>/', views.MaisonDetailView.as_view(), name='maison_detail'),
    path('contact/', views.contact, name='contact'),
    path('a-propos/', views.apropos, name='apropos'),
    
    # AJAX et API
    path('recherche-ajax/', views.recherche_ajax, name='recherche_ajax'),
    path('api/create-reservation/', views.create_reservation_ajax, name='create_reservation_ajax'),
    path('api/maisons-disponibles/', views.api_maisons_disponibles, name='api_maisons_disponibles'),
    path('api/disponibilites/<int:maison_id>/', views.api_disponibilites, name='api_disponibilites'),
    
    # NOUVELLES VUES
    # Dashboard gestionnaire public (différent de l'admin)
    path('gestionnaire/dashboard/', views.gestionnaire_dashboard, name='gestionnaire_dashboard'),
]