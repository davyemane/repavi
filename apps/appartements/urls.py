# apps/appartements/urls.py
from django.urls import path
from . import views

app_name = 'appartements'

urlpatterns = [
    # Liste et gestion selon cahier
    path('', views.liste_appartements, name='liste'),
    path('nouveau/', views.creer_appartement, name='creer'),
    path('<int:pk>/', views.detail_appartement, name='detail'),
    path('<int:pk>/modifier/', views.modifier_appartement, name='modifier'),
    path('<int:pk>/statut/', views.changer_statut_appartement, name='changer_statut'),
    
    # Photos par pièce selon cahier
    path('photos/', views.gerer_photos, name='photos'),
    path('<int:pk>/photo/ajouter/', views.ajouter_photo, name='ajouter_photo'),
    path('photo/<int:photo_pk>/supprimer/', views.supprimer_photo, name='supprimer_photo'),
]
