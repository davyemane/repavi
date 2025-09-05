# ==========================================
# apps/facturation/admin.py - Version simplifiée
# ==========================================
from django.contrib import admin
from .models import Facture, ParametresFacturation


@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    """Administration des factures RepAvi - Version simplifiée"""
    
    list_display = ['numero', 'client', 'date_emission', 'montant_ttc', 'statut']
    list_filter = ['statut', 'date_emission']
    search_fields = ['numero', 'client__nom', 'client__prenom']
    readonly_fields = ['numero', 'montant_ht', 'montant_tva', 'montant_ttc']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('numero', 'reservation', 'client', 'statut')
        }),
        ('Montants', {
            'fields': ('montant_ht', 'montant_tva', 'montant_ttc')
        }),
        ('Détails', {
            'fields': ('frais_menage', 'frais_service', 'remise', 'notes')
        }),
    )


@admin.register(ParametresFacturation)
class ParametresFacturationAdmin(admin.ModelAdmin):
    """Administration des paramètres de facturation"""
    
    fieldsets = (
        ('Informations Entreprise', {
            'fields': ('nom_entreprise', 'adresse', 'telephone', 'email')
        }),
        ('Paramètres', {
            'fields': ('taux_tva_defaut', 'frais_menage_defaut')
        }),
    )
    
    def has_add_permission(self, request):
        return not ParametresFacturation.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False