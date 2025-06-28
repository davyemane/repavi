# repavi/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Administration Django par défaut
    path('admin/', admin.site.urls),
    
    # Administration personnalisée RepAvi
    path('repavi-admin/', include('home.admin_urls')),
    
    # Site public
    path('', include('home.urls')),

    path('users/', include('users.urls')),  # ← Ajouter cette ligne

     # App réservations
    path('reservations/', include('reservations.urls')),

    # # meubles
    path('meubles/', include('meubles.urls')),

]

# Servir les fichiers média et statiques en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Ajouter django-browser-reload si présent
    try:
        urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]
    except ImportError:
        pass