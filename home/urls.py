from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.index, name='index'),
    path('maisons/', views.MaisonListView.as_view(), name='maisons_list'),
    path('maison/<slug:slug>/', views.MaisonDetailView.as_view(), name='maison_detail'),
    path('recherche-ajax/', views.recherche_ajax, name='recherche_ajax'),
    path('contact/', views.contact, name='contact'),
    path('a-propos/', views.apropos, name='apropos'),
]