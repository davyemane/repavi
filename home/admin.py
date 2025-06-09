# home/admin.py
from django.contrib import admin
from .models import Ville, CategorieMaison, Maison, PhotoMaison, Reservation

@admin.register(Ville)
class VilleAdmin(admin.ModelAdmin):
    list_display = ['nom', 'departement', 'code_postal', 'pays']
    list_filter = ['departement', 'pays']
    search_fields = ['nom', 'departement']

@admin.register(CategorieMaison)
class CategorieMaisonAdmin(admin.ModelAdmin):
    list_display = ['nom', 'couleur']
    list_editable = ['couleur']

class PhotoMaisonInline(admin.TabularInline):
    model = PhotoMaison
    extra = 1
    fields = ['image', 'titre', 'principale', 'ordre']

@admin.register(Maison)
class MaisonAdmin(admin.ModelAdmin):
    list_display = ['nom', 'ville', 'prix_par_nuit', 'capacite_personnes', 'disponible', 'featured']
    list_filter = ['disponible', 'featured', 'ville', 'categorie']
    search_fields = ['nom', 'description', 'ville__nom']
    list_editable = ['disponible', 'featured']
    prepopulated_fields = {'slug': ('nom',)}
    inlines = [PhotoMaisonInline]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'slug', 'description', 'categorie')
        }),
        ('Localisation', {
            'fields': ('adresse', 'ville')
        }),
        ('Détails', {
            'fields': ('capacite_personnes', 'nombre_chambres', 'nombre_salles_bain', 'superficie')
        }),
        ('Prix et disponibilité', {
            'fields': ('prix_par_nuit', 'disponible', 'featured')
        }),
        ('Équipements', {
            'fields': ('wifi', 'parking', 'piscine', 'jardin', 'climatisation', 'lave_vaisselle', 'machine_laver'),
            'classes': ('collapse',)
        }),
        ('Propriétaire', {
            'fields': ('proprietaire',)
        }),
    )

@admin.register(PhotoMaison)
class PhotoMaisonAdmin(admin.ModelAdmin):
    list_display = ['maison', 'titre', 'principale', 'ordre']
    list_filter = ['principale', 'maison']
    list_editable = ['principale', 'ordre']

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['maison', 'locataire', 'date_debut', 'date_fin', 'statut', 'prix_total']
    list_filter = ['statut', 'date_creation', 'maison__ville']
    search_fields = ['maison__nom', 'locataire__username', 'locataire__email']
    date_hierarchy = 'date_debut'
    
    fieldsets = (
        ('Réservation', {
            'fields': ('maison', 'locataire', 'date_debut', 'date_fin', 'nombre_personnes')
        }),
        ('Prix et statut', {
            'fields': ('prix_total', 'statut')
        }),
        ('Contact', {
            'fields': ('telephone', 'message')
        }),
    )