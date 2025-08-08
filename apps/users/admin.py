# ==========================================
# apps/users/admin.py - Administration des utilisateurs
# ==========================================
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Administration personnalisée des utilisateurs RepAvi
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'profil', 'is_active', 'date_joined')
    list_filter = ('profil', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'telephone')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informations RepAvi', {
            'fields': ('profil', 'telephone')
        }),
    )
    
    def get_queryset(self, request):
        """Seuls les Super Admin peuvent voir tous les utilisateurs"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Les gestionnaires ne voient que leur propre profil
        return qs.filter(pk=request.user.pk)
    
    def has_add_permission(self, request):
        """Seuls les Super Admin peuvent créer des utilisateurs"""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Seuls les Super Admin peuvent supprimer"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Super Admin : tout, Gestionnaire : son propre profil"""
        if request.user.is_superuser:
            return True
        if obj and obj.pk == request.user.pk:
            return True
        return False