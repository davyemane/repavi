# avis/urls.py
from django.urls import path
from . import views

app_name = 'avis'

urlpatterns = [
    # ============================================================================
    # URLS PUBLIQUES - CONSULTATION DES AVIS
    # ============================================================================
    
    # Liste des avis d'une maison
    path('maison/<slug:slug>/', 
         views.AvisListView.as_view(), 
         name='avis_list'),
    
    # Détail d'un avis en AJAX
    path('avis/<int:avis_id>/detail/', 
         views.avis_detail_ajax, 
         name='avis_detail_ajax'),
    
    # Widget avis pour inclusion dans d'autres pages
    path('widget/maison/<int:maison_id>/', 
         views.widget_avis_maison, 
         name='widget_avis_maison'),
    
    # ============================================================================
    # URLS CLIENT - CREATION ET GESTION D'AVIS
    # ============================================================================
    
    # Créer un nouvel avis
    path('maison/<slug:slug>/creer/', 
         views.CreerAvisView.as_view(), 
         name='creer_avis'),
    
    # Modifier un avis existant
    path('avis/<int:avis_id>/modifier/', 
         views.modifier_avis, 
         name='modifier_avis'),
    
    # Liste des avis de l'utilisateur connecté
    path('mes-avis/', 
         views.mes_avis, 
         name='mes_avis'),
    
    # ============================================================================
    # URLS GESTIONNAIRE - REPONSES ET MODERATION
    # ============================================================================
    
    # Tableau de bord des avis pour gestionnaires
    path('gestion/', 
         views.tableau_avis_gestionnaire, 
         name='tableau_avis_gestionnaire'),
    
    # Répondre à un avis
    path('avis/<int:avis_id>/repondre/', 
         views.repondre_avis, 
         name='repondre_avis'),
    
    # Modérer un avis (approuver/rejeter)
    path('avis/<int:avis_id>/moderer/', 
         views.moderer_avis, 
         name='moderer_avis'),
    
    # ============================================================================
    # URLS AJAX - INTERACTIONS DYNAMIQUES
    # ============================================================================
    
    # Liker/unliker un avis
    path('avis/<int:avis_id>/like/', 
         views.like_avis, 
         name='like_avis'),
    
    # Signaler un avis
    path('avis/<int:avis_id>/signaler/', 
         views.signaler_avis, 
         name='signaler_avis'),
    
    # ============================================================================
    # URLS ADMIN - GESTION AVANCEE
    # ============================================================================
    
    # Statistiques globales des avis
    path('admin/statistiques/', 
         views.statistiques_avis, 
         name='statistiques_avis'),
]


# ============================================================================
# URLS ALTERNATIVES (si intégration dans d'autres apps)
# ============================================================================

# Ces patterns peuvent être intégrés dans home/urls.py si nécessaire
alternative_patterns = [
    # Dans home/urls.py pour intégration transparente
    # path('maisons/<slug:slug>/avis/', include('avis.urls')),
    
    # Ou directement dans le main urls.py
    # path('avis/', include('avis.urls')),
]