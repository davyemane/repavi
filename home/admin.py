# home/admin.py
from django.contrib import admin
from .models import Ville, CategorieMaison, Maison, PhotoMaison, Reservation

# Configuration générale de l'admin Django
admin.site.site_header = "RepAvi - Administration Django"
admin.site.site_title = "RepAvi Admin"
admin.site.index_title = "Administration Django (Backup)"

# Administration basique pour backup
# (L'administration principale se trouve à /repavi-admin/)

@admin.register(Ville)
class VilleAdmin(admin.ModelAdmin):
    list_display = ['nom', 'departement', 'code_postal', 'pays']
    list_filter = ['departement', 'pays']
    search_fields = ['nom', 'departement']
    ordering = ['nom']

@admin.register(CategorieMaison)
class CategorieMaisonAdmin(admin.ModelAdmin):
    list_display = ['nom', 'couleur', 'description']
    list_editable = ['couleur']
    search_fields = ['nom']

class PhotoMaisonInline(admin.TabularInline):
    model = PhotoMaison
    extra = 1
    fields = ['image', 'titre', 'principale', 'ordre']

@admin.register(Maison)
class MaisonAdmin(admin.ModelAdmin):
    list_display = ['nom', 'ville', 'prix_par_nuit', 'disponible', 'featured']
    list_filter = ['disponible', 'featured', 'ville', 'categorie']
    search_fields = ['nom', 'description', 'ville__nom']
    list_editable = ['disponible', 'featured']
    prepopulated_fields = {'slug': ('nom',)}
    inlines = [PhotoMaisonInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('nom', 'slug', 'description', 'categorie')
        }),
        ('Localisation', {
            'fields': ('adresse', 'ville')
        }),
        ('Caractéristiques', {
            'fields': ('capacite_personnes', 'nombre_chambres', 'nombre_salles_bain', 'superficie')
        }),
        ('Prix et statut', {
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
    list_filter = ['statut', 'date_creation']
    search_fields = ['maison__nom', 'locataire__username']
    date_hierarchy = 'date_debut'