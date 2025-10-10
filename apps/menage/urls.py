from django.urls import path
from . import views

app_name = 'menage'

urlpatterns = [
    path('', views.planning_menage, name='planning'),
    path('tache/<int:tache_pk>/', views.detail_tache, name='detail'),
    path('historique/', views.historique_menage, name='historique'),
]