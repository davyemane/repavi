# avis/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Avis, PhotoAvis, LikeAvis, SignalementAvis

class PhotoAvisInline(admin.TabularInline):
    """Inline pour les photos d'avis"""
    model = PhotoAvis
    extra = 0
    fields = ['image', 'legende', 'ordre']
    readonly_fields = ['taille_fichier']

@admin.register(Avis)
class AvisAdmin(admin.ModelAdmin):
    """Administration des avis"""
    
    list_display = [
        'id', 'client_link', 'maison_link', 'note_display', 
        'statut_badge', 'date_creation', 'actions_admin'
    ]
    
    list_filter = [
        'statut_moderation', 'note', 'recommande', 
        'date_creation', 'maison__ville'
    ]
    
    search_fields = [
        'client__first_name', 'client__last_name', 'client__email',
        'maison__nom', 'titre', 'commentaire'
    ]
    
    readonly_fields = [
        'date_creation', 'date_modification', 'nombre_likes', 
        'nombre_signalements', 'est_recent'
    ]
    
    fieldsets = (
        ('Informations de base', {
            'fields': (
                ('client', 'maison'),
                ('note', 'titre'),
                'commentaire',
                ('date_sejour', 'duree_sejour'),
                'recommande'
            )
        }),
        ('Modération', {
            'fields': (
                ('statut_moderation', 'modere_par'),
                'date_moderation',
                'raison_rejet'
            )
        }),
        ('Réponse du gestionnaire', {
            'fields': (
                'reponse_gestionnaire',
                ('reponse_par', 'date_reponse')
            ),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': (
                ('date_creation', 'date_modification'),
                ('nombre_likes', 'nombre_signalements'),
                'est_recent'
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [PhotoAvisInline]
    
    actions = ['approuver_avis', 'rejeter_avis', 'marquer_signale']
    
    def client_link(self, obj):
        """Lien vers le client"""
        url = reverse('admin:users_user_change', args=[obj.client.pk])
        return format_html('<a href="{}">{}</a>', url, obj.client.nom_complet)
    client_link.short_description = 'Client'
    
    def maison_link(self, obj):
        """Lien vers la maison"""
        url = reverse('admin:home_maison_change', args=[obj.maison.pk])
        return format_html('<a href="{}">{}</a>', url, obj.maison.nom)
    maison_link.short_description = 'Maison'
    
    def note_display(self, obj):
        """Affichage des étoiles"""
        stars = "★" * obj.note + "☆" * (5 - obj.note)
        return format_html('<span style="color: #fbbf24; font-size: 16px;">{}</span>', stars)
    note_display.short_description = 'Note'
    
    def statut_badge(self, obj):
        """Badge coloré pour le statut"""
        colors = {
            'en_attente': '#f59e0b',
            'approuve': '#10b981',
            'rejete': '#ef4444',
            'signale': '#f97316'
        }
        color = colors.get(obj.statut_moderation, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_statut_moderation_display()
        )
    statut_badge.short_description = 'Statut'
    
    def actions_admin(self, obj):
        """Actions rapides"""
        actions = []
        
        if obj.statut_moderation == 'en_attente':
            actions.append('<a href="#" onclick="approuverAvis({})" style="color: #10b981;">✓ Approuver</a>'.format(obj.pk))
            actions.append('<a href="#" onclick="rejeterAvis({})" style="color: #ef4444;">✗ Rejeter</a>'.format(obj.pk))
        
        if obj.avis.count() > 0:
            actions.append('<a href="{}">🖼️ Photos ({})</a>'.format(
                reverse('admin:avis_photoavis_changelist') + f'?avis__id__exact={obj.pk}',
                obj.photos.count()
            ))
        
        return format_html(' | '.join(actions)) if actions else '-'
    actions_admin.short_description = 'Actions'
    
    def approuver_avis(self, request, queryset):
        """Action pour approuver des avis"""
        count = 0
        for avis in queryset.filter(statut_moderation='en_attente'):
            avis.approuver(moderateur=request.user)
            count += 1
        
        self.message_user(request, f'{count} avis approuvé(s) avec succès.')
    approuver_avis.short_description = "Approuver les avis sélectionnés"
    
    def rejeter_avis(self, request, queryset):
        """Action pour rejeter des avis"""
        count = 0
        for avis in queryset.filter(statut_moderation='en_attente'):
            avis.rejeter("Rejeté en masse par l'administrateur", moderateur=request.user)
            count += 1
        
        self.message_user(request, f'{count} avis rejeté(s) avec succès.')
    rejeter_avis.short_description = "Rejeter les avis sélectionnés"
    
    def marquer_signale(self, request, queryset):
        """Action pour marquer comme signalé"""
        count = queryset.update(statut_moderation='signale')
        self.message_user(request, f'{count} avis marqué(s) comme signalé(s).')
    marquer_signale.short_description = "Marquer comme signalé"
    
    def get_queryset(self, request):
        """Optimiser les requêtes"""
        return super().get_queryset(request).select_related(
            'client', 'maison', 'modere_par', 'reponse_par'
        ).prefetch_related('photos', 'likes', 'signalements')
    
    class Media:
        js = ('admin/js/avis_admin.js',)  # JavaScript personnalisé
        css = {
            'all': ('admin/css/avis_admin.css',)  # CSS personnalisé
        }


@admin.register(PhotoAvis)
class PhotoAvisAdmin(admin.ModelAdmin):
    """Administration des photos d'avis"""
    
    list_display = ['id', 'avis_link', 'image_preview', 'legende', 'ordre', 'taille_fichier_display']
    list_filter = ['date_ajout', 'avis__statut_moderation']
    search_fields = ['avis__titre', 'legende', 'avis__client__first_name']
    
    def avis_link(self, obj):
        """Lien vers l'avis"""
        url = reverse('admin:avis_avis_change', args=[obj.avis.pk])
        return format_html('<a href="{}">{}</a>', url, f"Avis #{obj.avis.pk}")
    avis_link.short_description = 'Avis'
    
    def image_preview(self, obj):
        """Aperçu de l'image"""
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 60px; height: 45px; object-fit: cover; border-radius: 4px;">', 
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Aperçu'
    
    def taille_fichier_display(self, obj):
        """Affichage de la taille du fichier"""
        if obj.taille_fichier:
            if obj.taille_fichier > 1024 * 1024:  # > 1MB
                return f"{obj.taille_fichier / (1024 * 1024):.1f} MB"
            elif obj.taille_fichier > 1024:  # > 1KB
                return f"{obj.taille_fichier / 1024:.1f} KB"
            else:
                return f"{obj.taille_fichier} B"
        return '-'
    taille_fichier_display.short_description = 'Taille'


@admin.register(LikeAvis)
class LikeAvisAdmin(admin.ModelAdmin):
    """Administration des likes d'avis"""
    
    list_display = ['id', 'avis_link', 'user_link', 'date_creation']
    list_filter = ['date_creation']
    search_fields = ['avis__titre', 'user__first_name', 'user__last_name']
    
    def avis_link(self, obj):
        """Lien vers l'avis"""
        url = reverse('admin:avis_avis_change', args=[obj.avis.pk])
        return format_html('<a href="{}">{}</a>', url, f"Avis #{obj.avis.pk}")
    avis_link.short_description = 'Avis'
    
    def user_link(self, obj):
        """Lien vers l'utilisateur"""
        url = reverse('admin:users_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.nom_complet)
    user_link.short_description = 'Utilisateur'


@admin.register(SignalementAvis)
class SignalementAvisAdmin(admin.ModelAdmin):
    """Administration des signalements d'avis"""
    
    list_display = [
        'id', 'avis_link', 'user_link', 'raison_display', 
        'traite_badge', 'date_creation', 'actions_signalement'
    ]
    
    list_filter = ['raison', 'traite', 'date_creation']
    search_fields = ['avis__titre', 'user__first_name', 'commentaire']
    
    fieldsets = (
        ('Informations du signalement', {
            'fields': (
                ('avis', 'user'),
                ('raison', 'commentaire'),
                'date_creation'
            )
        }),
        ('Traitement', {
            'fields': (
                ('traite', 'traite_par'),
            )
        })
    )
    
    actions = ['marquer_traite', 'marquer_non_traite']
    
    def avis_link(self, obj):
        """Lien vers l'avis signalé"""
        url = reverse('admin:avis_avis_change', args=[obj.avis.pk])
        return format_html('<a href="{}">{}</a>', url, f"Avis #{obj.avis.pk}")
    avis_link.short_description = 'Avis signalé'
    
    def user_link(self, obj):
        """Lien vers l'utilisateur qui signale"""
        url = reverse('admin:users_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.nom_complet)
    user_link.short_description = 'Signalé par'
    
    def raison_display(self, obj):
        """Affichage coloré de la raison"""
        colors = {
            'spam': '#ef4444',
            'faux': '#f97316',
            'inapproprie': '#dc2626',
            'hors_sujet': '#f59e0b',
            'insultes': '#b91c1c',
            'autre': '#6b7280'
        }
        color = colors.get(obj.raison, '#6b7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_raison_display()
        )
    raison_display.short_description = 'Raison'
    
    def traite_badge(self, obj):
        """Badge pour le statut de traitement"""
        if obj.traite:
            return format_html(
                '<span style="background-color: #10b981; color: white; padding: 3px 8px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">✓ Traité</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #f59e0b; color: white; padding: 3px 8px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">⏳ En attente</span>'
            )
    traite_badge.short_description = 'Statut'
    
    def actions_signalement(self, obj):
        """Actions rapides pour les signalements"""
        actions = []
        
        if not obj.traite:
            actions.append('<a href="#" onclick="marquerTraite({})" style="color: #10b981;">✓ Marquer traité</a>'.format(obj.pk))
        
        # Lien vers l'avis pour modération
        actions.append('<a href="{}" style="color: #3b82f6;">👁️ Voir avis</a>'.format(
            reverse('admin:avis_avis_change', args=[obj.avis.pk])
        ))
        
        return format_html(' | '.join(actions)) if actions else '-'
    actions_signalement.short_description = 'Actions'
    
    def marquer_traite(self, request, queryset):
        """Action pour marquer comme traité"""
        count = queryset.update(traite=True, traite_par=request.user)
        self.message_user(request, f'{count} signalement(s) marqué(s) comme traité(s).')
    marquer_traite.short_description = "Marquer comme traité"
    
    def marquer_non_traite(self, request, queryset):
        """Action pour marquer comme non traité"""
        count = queryset.update(traite=False, traite_par=None)
        self.message_user(request, f'{count} signalement(s) marqué(s) comme non traité(s).')
    marquer_non_traite.short_description = "Marquer comme non traité"
    
    def get_queryset(self, request):
        """Optimiser les requêtes"""
        return super().get_queryset(request).select_related(
            'avis', 'user', 'traite_par'
        )


# Configuration de l'admin pour améliorer l'interface
admin.site.site_header = "Administration RepAvi - Avis"
admin.site.site_title = "RepAvi Admin"
admin.site.index_title = "Gestion des avis et modération"