# avis/urls.py
from django.urls import path
from . import views

app_name = 'avis'

urlpatterns = [
    # Créer un avis
    path('maison/<slug:maison_slug>/creer/', views.creer_avis, name='creer_avis'),
    
    # Récupérer la liste des avis (pagination AJAX)
    path('maison/<slug:maison_slug>/list/', views.get_avis_list, name='avis_list'),
    
    # Supprimer un avis (admin seulement)
#    path('avis/<int:avis_id>/supprimer/', views.supprimer_avis, name='supprimer_avis'),
]