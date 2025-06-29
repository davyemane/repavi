from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from .models import TypeMeuble, Meuble, HistoriqueEtatMeuble, PhotoMeuble, InventaireMaison


@admin.register(TypeMeuble)
class TypeMeubleAdmin(admin.ModelAdmin):
    list_display = ['nom', 'categorie', 'nombre_meubles', 'icone']
    list_filter = ['categorie']
    search_fields = ['nom', 'description']
    ordering = ['categorie', 'nom']
    
    def nombre_meubles(self, obj):
        return obj.nombre_meubles
    nombre_meubles.short_description = 'Nombre de meubles'


class PhotoMeubleInline(admin.TabularInline):
    model = PhotoMeuble
    extra = 1
    fields = ['image', 'titre', 'type_photo']
    readonly_fields = ['date_prise']


class HistoriqueEtatMeubleInline(admin.TabularInline):
    model = HistoriqueEtatMeuble
    extra = 0
    fields = ['ancien_etat', 'nouvel_etat', 'date_changement', 'motif', 'cout']
    readonly_fields = ['date_changement']
    
    def has_add_permission(self, request, obj=None):
        return False  # Historique créé automatiquement


@admin.register(Meuble)
class MeubleAdmin(admin.ModelAdmin):
    list_display = [
        'numero_serie', 'nom', 'type_meuble', 'maison_info', 
        'piece', 'etat_badge', 'age_display', 'verification_status'
    ]
    list_filter = [
        'etat', 'type_meuble__categorie', 'piece', 
        'maison__gestionnaire', 'date_entree'
    ]
    search_fields = [
        'nom', 'numero_serie', 'maison__nom', 'maison__numero',
        'marque', 'modele'
    ]
    readonly_fields = [
        'date_creation', 'date_modification', 'age_en_mois',
        'depreciation_estimee', 'necessite_verification'
    ]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('nom', 'type_meuble', 'numero_serie', 'maison')
        }),
        ('État et condition', {
            'fields': ('etat', 'date_entree', 'date_derniere_verification')
        }),
        ('Emplacement', {
            'fields': ('piece',)
        }),
        ('Détails du meuble', {
            'fields': ('marque', 'modele', 'couleur', 'materiaux', 'dimensions'),
            'classes': ('collapse',)
        }),
        ('Informations financières', {
            'fields': ('prix_achat', 'valeur_actuelle', 'depreciation_estimee'),
            'classes': ('collapse',)
        }),
        ('Notes et observations', {
            'fields': ('notes',)
        }),
        ('Métadonnées', {
            'fields': ('ajoute_par', 'date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('age_en_mois', 'necessite_verification'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [PhotoMeubleInline, HistoriqueEtatMeubleInline]
    
    def maison_info(self, obj):
        return f"{obj.maison.numero} - {obj.maison.nom}"
    maison_info.short_description = 'Maison'
    
    def etat_badge(self, obj):
        colors = {
            'bon': 'green',
            'usage': 'orange', 
            'defectueux': 'red',
            'hors_service': 'gray'
        }
        color = colors.get(obj.etat, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_etat_display()
        )
    etat_badge.short_description = 'État'
    
    def age_display(self, obj):
        mois = obj.age_en_mois
        if mois < 12:
            return f"{mois} mois"
        else:
            annees = mois // 12
            mois_restants = mois % 12
            if mois_restants == 0:
                return f"{annees} an{'s' if annees > 1 else ''}"
            return f"{annees}a {mois_restants}m"
    age_display.short_description = 'Âge'
    
    def verification_status(self, obj):
        if obj.necessite_verification:
            return format_html(
                '<span style="color: red;">⚠️ À vérifier</span>'
            )
        return format_html(
            '<span style="color: green;">✅ OK</span>'
        )
    verification_status.short_description = 'Vérification'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'maison', 'type_meuble', 'ajoute_par'
        )
    
    actions = ['marquer_defectueux', 'marquer_bon_etat', 'programmer_verification']
    
    def marquer_defectueux(self, request, queryset):
        count = queryset.update(etat='defectueux')
        self.message_user(request, f'{count} meuble(s) marqué(s) comme défectueux.')
    marquer_defectueux.short_description = 'Marquer comme défectueux'
    
    def marquer_bon_etat(self, request, queryset):
        count = queryset.update(etat='bon')
        self.message_user(request, f'{count} meuble(s) marqué(s) en bon état.')
    marquer_bon_etat.short_description = 'Marquer en bon état'
    
    def programmer_verification(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(date_derniere_verification=None)
        self.message_user(request, f'{count} meuble(s) programmé(s) pour vérification.')
    programmer_verification.short_description = 'Programmer vérification'


@admin.register(HistoriqueEtatMeuble)
class HistoriqueEtatMeubleAdmin(admin.ModelAdmin):
    list_display = [
        'meuble', 'ancien_etat', 'nouvel_etat', 
        'date_changement', 'modifie_par', 'cout'
    ]
    list_filter = ['ancien_etat', 'nouvel_etat', 'date_changement']
    search_fields = ['meuble__nom', 'meuble__numero_serie', 'motif']
    readonly_fields = ['date_changement']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'meuble', 'modifie_par'
        )


@admin.register(PhotoMeuble)
class PhotoMeubleAdmin(admin.ModelAdmin):
    list_display = ['meuble', 'titre', 'type_photo', 'date_prise']
    list_filter = ['type_photo', 'date_prise']
    search_fields = ['meuble__nom', 'titre']
    readonly_fields = ['date_prise']


@admin.register(InventaireMaison)
class InventaireMaisonAdmin(admin.ModelAdmin):
    list_display = [
        'maison', 'type_inventaire', 'date_inventaire', 
        'nombre_meubles_total', 'pourcentage_bon_etat_display',
        'effectue_par'
    ]
    list_filter = ['type_inventaire', 'date_inventaire', 'maison__gestionnaire']
    search_fields = ['maison__nom', 'maison__numero', 'observations']
    readonly_fields = [
        'date_inventaire', 'nombre_meubles_total', 
        'nombre_meubles_bon_etat', 'nombre_meubles_defectueux',
        'pourcentage_bon_etat'
    ]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('maison', 'type_inventaire', 'effectue_par')
        }),
        ('Statistiques', {
            'fields': (
                'nombre_meubles_total', 'nombre_meubles_bon_etat', 
                'nombre_meubles_defectueux', 'pourcentage_bon_etat'
            )
        }),
        ('Observations', {
            'fields': ('observations',)
        }),
        ('Métadonnées', {
            'fields': ('date_inventaire',),
            'classes': ('collapse',)
        })
    )
    
    def pourcentage_bon_etat_display(self, obj):
        pourcentage = obj.pourcentage_bon_etat
        if pourcentage >= 80:
            color = 'green'
        elif pourcentage >= 60:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            pourcentage
        )
    pourcentage_bon_etat_display.short_description = '% Bon état'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Nouveau inventaire
            obj.effectue_par = request.user
        super().save_model(request, obj, form, change)
        # Recalculer les statistiques
        obj.calculer_statistiques()
    
    actions = ['recalculer_statistiques']
    
    def recalculer_statistiques(self, request, queryset):
        for inventaire in queryset:
            inventaire.calculer_statistiques()
        self.message_user(request, f'Statistiques recalculées pour {queryset.count()} inventaire(s).')
    recalculer_statistiques.short_description = 'Recalculer les statistiques'