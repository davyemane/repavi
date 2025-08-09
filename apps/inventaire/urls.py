from django.urls import path
from . import views
from .pdf_utils import generer_pdf_inventaire, generer_pdf_general

app_name = 'inventaire'

urlpatterns = [
    # Vue générale
    path('', views.inventaire_general, name='general'),
    
    # Inventaire par appartement selon cahier
    path('appartement/<int:appartement_pk>/', views.inventaire_par_appartement, name='appartement'),
    
    # Gestion équipements selon cahier
    path('appartement/<int:appartement_pk>/ajouter/', views.ajouter_equipement, name='ajouter_equipement'),
    path('equipement/<int:pk>/modifier/', views.modifier_equipement, name='modifier_equipement'),
    path('equipement/<int:pk>/supprimer/', views.supprimer_equipement, name='supprimer_equipement'),
    
    # Changement d'état en 1 clic selon cahier
    path('equipement/<int:pk>/etat/', views.changer_etat_equipement, name='changer_etat'),
    
    # Valeur totale par appartement selon cahier
    path('appartement/<int:appartement_pk>/valeur/', views.valeur_totale_appartement, name='valeur_totale'),
    
    # PDF selon cahier
    path('appartement/<int:appartement_pk>/pdf/', generer_pdf_inventaire, name='pdf_appartement'),
    path('pdf/', generer_pdf_general, name='pdf_general'),
]