from django.contrib import admin
from .models import TacheMenage


@admin.register(TacheMenage)
class TacheMenageAdmin(admin.ModelAdmin):
    list_display = [
        'appartement', 'date_prevue', 'statut', 
        'reservation', 'date_creation'
    ]
    list_filter = ['statut', 'date_prevue', 'date_creation']
    search_fields = ['appartement__numero', 'rapport']
    readonly_fields = ['date_creation', 'date_completion']
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('appartement', 'reservation', 'date_prevue', 'statut')
        }),
        ('Rapport', {
            'fields': ('rapport',)
        }),
        ('Dates', {
            'fields': ('date_creation', 'date_completion'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'appartement', 'reservation'
        )