# repavi/urls.py - URLs principales
from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from apps.users.views import DashboardView

urlpatterns = [
    # Admin Django (interface de backup)
    path('admin/', admin.site.urls),
    
    # Authentification
    path('', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page=reverse_lazy('login')), name='logout'),
    
    # Dashboard principal (après connexion)
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    
    # Modules principaux (selon cahier des charges)
    path('appartements/', include('apps.appartements.urls')),
    path('clients/', include('apps.clients.urls')),
    path('reservations/', include('apps.reservations.urls')),
    path('paiements/', include('apps.paiements.urls')),
    path('inventaire/', include('apps.inventaire.urls')),
    path('comptabilite/', include('apps.comptabilite.urls')),
    path('menage/', include('apps.menage.urls')),
    path('facturation/', include('apps.facturation.urls')),
    
    # Gestion utilisateurs (pour super admin)
    path('users/', include('apps.users.urls')),
]

# Fichiers média en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]

# Configuration du site admin
admin.site.site_header = 'RepAvi Lodges - Administration'
admin.site.site_title = 'RepAvi Admin'
admin.site.index_title = 'Interface de backup'