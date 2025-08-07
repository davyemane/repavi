# ==========================================
# apps/appartements/admin.py - Administration des appartements
# ==========================================
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Appartement, PhotoAppartement

class PhotoAppartementInline(admin.TabularInline):
    """Photos intégrées dans la fiche appartement"""
    model = PhotoAppartement
    extra = 1
    fields = ['nom_piece', 'photo', 'est_principale', 'ordre']
    readonly_fields = ['apercu_photo']
    
    def apercu_photo(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.photo.url
            )
        return "Aucune photo"
    apercu_photo.short_description = "Aperçu"

@admin.register(Appartement)
class AppartementAdmin(admin.ModelAdmin):
    """
    Administration des appartements RepAvi
    """
    list_display = [
        'numero', 'type_logement_display', 'maison', 'prix_par_nuit',
        'statut_display', 'nb_photos', 'nb_equipements', 'date_creation'
    ]
    list_filter = ['statut', 'type_logement', 'maison']
    search_fields = ['numero', 'maison']
    ordering = ['numero']
    list_per_page = 25
    
    fieldsets = (
        ('Identification', {
            'fields': ('numero', 'type_logement', 'maison')
        }),
        ('Tarification', {
            'fields': ('prix_par_nuit',),
            'description': 'Prix unique et simple par nuit selon cahier des charges'
        }),
        ('État', {
            'fields': ('statut',)
        }),
        ('Équipements', {
            'fields': ('equipements',),
            'description': 'Liste simple : TV, Frigo, Climatisation, etc.'
        }),
    )
    
    inlines = [PhotoAppartementInline]
    
    def type_logement_display(self, obj):
        """Affichage coloré du type"""
        colors = {
            'studio': '#f59e0b',
            't1': '#3b82f6', 
            't2': '#10b981'
        }
        color = colors.get(obj.type_logement, '#6b7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_type_logement_display()
        )
    type_logement_display.short_description = 'Type'
    type_logement_display.admin_order_field = 'type_logement'
    
    def statut_display(self, obj):
        """Affichage coloré du statut"""
        colors = {
            'disponible': '#10b981',
            'occupe': '#f59e0b',
            'maintenance': '#ef4444'
        }
        color = colors.get(obj.statut, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_display.short_description = 'Statut'
    statut_display.admin_order_field = 'statut'
    
    def nb_photos(self, obj):
        """Nombre de photos"""
        count = obj.photos.count()
        if count > 0:
            return format_html(
                '<span style="color: #10b981;">📷 {}</span>',
                count
            )
        return format_html('<span style="color: #6b7280;">Aucune</span>')
    nb_photos.short_description = 'Photos'
    
    def nb_equipements(self, obj):
        """Nombre d'équipements"""
        count = len(obj.equipements) if obj.equipements else 0
        if count > 0:
            return format_html(
                '<span style="color: #3b82f6;">🔧 {}</span>',
                count
            )
        return format_html('<span style="color: #6b7280;">Aucun</span>')
    nb_equipements.short_description = 'Équipements'
    
    def get_queryset(self, request):
        """Optimiser les requêtes"""
        return super().get_queryset(request).prefetch_related('photos')
    
    actions = ['marquer_disponible', 'marquer_maintenance', 'exporter_appartements']
    
    def marquer_disponible(self, request, queryset):
        """Action pour marquer comme disponible"""
        updated = queryset.update(statut='disponible')
        self.message_user(request, f'{updated} appartement(s) marqué(s) comme disponible(s).')
    marquer_disponible.short_description = 'Marquer comme disponible'
    
    def marquer_maintenance(self, request, queryset):
        """Action pour marquer en maintenance"""
        updated = queryset.update(statut='maintenance')
        self.message_user(request, f'{updated} appartement(s) marqué(s) en maintenance.')
    marquer_maintenance.short_description = 'Marquer en maintenance'
    
    def exporter_appartements(self, request, queryset):
        """Export simple des appartements"""
        # À implémenter selon les besoins
        self.message_user(request, 'Export en cours de développement.')
    exporter_appartements.short_description = 'Exporter la sélection'

@admin.register(PhotoAppartement)
class PhotoAppartementAdmin(admin.ModelAdmin):
    """
    Administration des photos d'appartements
    """
    list_display = ['appartement', 'nom_piece', 'est_principale', 'ordre', 'apercu_photo']
    list_filter = ['est_principale', 'nom_piece']
    search_fields = ['appartement__numero', 'nom_piece']
    ordering = ['appartement__numero', 'ordre', 'nom_piece']
    list_per_page = 30
    
    def apercu_photo(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 80px; height: 60px; object-fit: cover; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                obj.photo.url
            )
        return "Aucune photo"
    apercu_photo.short_description = "Aperçu"
    
    def get_queryset(self, request):
        """Optimiser les requêtes"""
        return super().get_queryset(request).select_related('appartement')

# Configuration de l'admin
admin.site.site_header = "RepAvi Lodges - Administration"
admin.site.site_title = "RepAvi Admin"
admin.site.index_title = "Gestion des Appartements et Réservations"