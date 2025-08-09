# ==========================================
# apps/inventaire/admin.py - Administration inventaire selon cahier
# ==========================================
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import EquipementAppartement

@admin.register(EquipementAppartement)
class EquipementAppartementAdmin(admin.ModelAdmin):
    """
    Administration des équipements selon cahier des charges
    Interface de backup technique simplifiée
    """
    
    list_display = [
        'nom_equipement_display',
        'appartement', 
        'etat_display',
        'prix_achat_display',
        'date_achat',
        'photo_display'
    ]
    
    list_filter = [
        'etat',
        'appartement__numero',
        'appartement__type_logement',
        'date_achat',
        'date_creation'
    ]
    
    search_fields = [
        'nom',
        'appartement__numero',
        'commentaire',
        'appartement__maison'
    ]
    
    readonly_fields = [
        'date_creation',
        'date_modification'
    ]
    
    fieldsets = (
        ('Informations Équipement', {
            'fields': ('nom', 'etat', 'appartement')
        }),
        ('Informations Financières', {
            'fields': ('prix_achat', 'date_achat')
        }),
        ('Détails', {
            'fields': ('photo', 'commentaire'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'marquer_bon_etat',
        'marquer_usage',
        'marquer_defectueux', 
        'marquer_hors_service'
    ]
    
    def nom_equipement_display(self, obj):
        """Affichage du nom avec icône selon état"""
        icones = {
            'bon': '✅',
            'usage': '🔵', 
            'defectueux': '⚠️',
            'hors_service': '❌'
        }
        icone = icones.get(obj.etat, '❓')
        return format_html('{} {}', icone, obj.nom)
    nom_equipement_display.short_description = 'Équipement'
    nom_equipement_display.admin_order_field = 'nom'
    
    def etat_display(self, obj):
        """Affichage coloré de l'état selon cahier"""
        couleurs = {
            'bon': '#10b981',
            'usage': '#3b82f6',
            'defectueux': '#f59e0b', 
            'hors_service': '#ef4444'
        }
        couleur = couleurs.get(obj.etat, '#6b7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            couleur,
            obj.get_etat_display()
        )
    etat_display.short_description = 'État'
    etat_display.admin_order_field = 'etat'
    
    def prix_achat_display(self, obj):
        """Affichage formaté du prix selon cahier"""
        return format_html('{:,.0f} FCFA', obj.prix_achat)
    prix_achat_display.short_description = 'Prix d\'achat'
    prix_achat_display.admin_order_field = 'prix_achat'
    
    def photo_display(self, obj):
        """Miniature de la photo"""
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;" />',
                obj.photo.url
            )
        return '📷 Aucune'
    photo_display.short_description = 'Photo'
    
    # Actions groupées selon cahier
    def marquer_bon_etat(self, request, queryset):
        """Marquer les équipements sélectionnés comme en bon état"""
        count = queryset.update(etat='bon')
        self.message_user(request, f'{count} équipement(s) marqué(s) en bon état.')
    marquer_bon_etat.short_description = "Marquer comme 'Bon état'"
    
    def marquer_usage(self, request, queryset):
        """Marquer les équipements sélectionnés comme en usage"""
        count = queryset.update(etat='usage')
        self.message_user(request, f'{count} équipement(s) marqué(s) en usage.')
    marquer_usage.short_description = "Marquer comme 'Usage'"
    
    def marquer_defectueux(self, request, queryset):
        """Marquer les équipements sélectionnés comme défectueux"""
        count = queryset.update(etat='defectueux')
        self.message_user(request, f'{count} équipement(s) marqué(s) comme défectueux.')
    marquer_defectueux.short_description = "Marquer comme 'Défectueux'"
    
    def marquer_hors_service(self, request, queryset):
        """Marquer les équipements sélectionnés comme hors service"""
        count = queryset.update(etat='hors_service')
        self.message_user(request, f'{count} équipement(s) marqué(s) hors service.')
    marquer_hors_service.short_description = "Marquer comme 'Hors service'"
    
    def changelist_view(self, request, extra_context=None):
        """Ajout de statistiques dans la vue liste selon cahier"""
        extra_context = extra_context or {}
        
        # Statistiques globales
        queryset = self.get_queryset(request)
        extra_context['total_equipements'] = queryset.count()
        extra_context['valeur_totale'] = queryset.aggregate(
            total=Sum('prix_achat')
        )['total'] or 0
        
        # Statistiques par état
        stats_etats = {}
        for etat_code, etat_nom in EquipementAppartement.ETAT_CHOICES:
            stats = queryset.filter(etat=etat_code).aggregate(
                count=Count('id'),
                valeur=Sum('prix_achat')
            )
            stats_etats[etat_code] = {
                'nom': etat_nom,
                'count': stats['count'] or 0,
                'valeur': stats['valeur'] or 0
            }
        extra_context['stats_etats'] = stats_etats
        
        return super().changelist_view(request, extra_context=extra_context)

# Configuration pour l'administration selon cahier
admin.site.site_header = "RepAvi Lodges - Administration de Backup"
admin.site.site_title = "RepAvi Admin"
admin.site.index_title = "Interface de backup technique"