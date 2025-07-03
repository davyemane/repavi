# avis/admin.py
from django.contrib import admin
from .models import Avis

@admin.register(Avis)
class AvisAdmin(admin.ModelAdmin):
    list_display = ['user', 'maison', 'note', 'date_creation', 'commentaire_court']
    list_filter = ['note', 'date_creation', 'maison']
    search_fields = ['user__username', 'maison__nom', 'commentaire']
    readonly_fields = ['date_creation']
    ordering = ['-date_creation']
    
    def commentaire_court(self, obj):
        return obj.commentaire[:50] + "..." if len(obj.commentaire) > 50 else obj.commentaire
    commentaire_court.short_description = "Commentaire"
    
    # Actions pour supprimer en masse
    actions = ['supprimer_avis_selectionnes']
    
    def supprimer_avis_selectionnes(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} avis supprimé(s) avec succès.")
    supprimer_avis_selectionnes.short_description = "Supprimer les avis sélectionnés"