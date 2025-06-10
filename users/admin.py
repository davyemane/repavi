# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, ProfilProprietaire, ProfilLocataire, TokenVerificationEmail, PasswordResetToken

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'type_utilisateur', 'email_verifie', 'is_active', 'date_joined')
    list_filter = ('type_utilisateur', 'email_verifie', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'telephone')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'telephone', 'date_naissance', 'photo_profil')
        }),
        ('Adresse', {
            'fields': ('adresse', 'ville', 'code_postal', 'pays'),
            'classes': ('collapse',)
        }),
        ('Type et statut', {
            'fields': ('type_utilisateur', 'email_verifie', 'telephone_verifie', 'identite_verifiee')
        }),
        ('Préférences', {
            'fields': ('newsletter', 'notifications_email', 'notifications_sms'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Dates importantes', {
            'fields': ('last_login', 'date_joined', 'date_derniere_connexion_complete'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'type_utilisateur', 'password1', 'password2'),
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

@admin.register(ProfilProprietaire)
class ProfilProprietaireAdmin(admin.ModelAdmin):
    list_display = ('user', 'verifie', 'note_moyenne', 'nombre_evaluations', 'auto_acceptation')
    list_filter = ('verifie', 'auto_acceptation')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'siret', 'raison_sociale')
    readonly_fields = ('note_moyenne', 'nombre_evaluations')
    
    fieldsets = (
        ('Utilisateur', {'fields': ('user',)}),
        ('Informations légales', {
            'fields': ('siret', 'raison_sociale'),
            'classes': ('collapse',)
        }),
        ('Informations bancaires', {
            'fields': ('iban', 'bic'),
            'classes': ('collapse',)
        }),
        ('Documents', {
            'fields': ('piece_identite', 'justificatif_domicile', 'kbis'),
            'classes': ('collapse',)
        }),
        ('Statut et évaluations', {
            'fields': ('verifie', 'note_moyenne', 'nombre_evaluations')
        }),
        ('Préférences', {
            'fields': ('auto_acceptation', 'delai_reponse_max')
        }),
    )

@admin.register(ProfilLocataire)
class ProfilLocataireAdmin(admin.ModelAdmin):
    list_display = ('user', 'type_sejour_prefere', 'nombre_sejours', 'note_moyenne')
    list_filter = ('type_sejour_prefere', 'langue_preferee')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('nombre_sejours', 'note_moyenne', 'nombre_evaluations')
    
    fieldsets = (
        ('Utilisateur', {'fields': ('user',)}),
        ('Préférences', {
            'fields': ('type_sejour_prefere', 'langue_preferee')
        }),
        ('Historique', {
            'fields': ('nombre_sejours', 'note_moyenne', 'nombre_evaluations')
        }),
        ('Documents', {
            'fields': ('piece_identite',),
            'classes': ('collapse',)
        }),
    )

@admin.register(TokenVerificationEmail)
class TokenVerificationEmailAdmin(admin.ModelAdmin):
    list_display = ('user', 'token_short', 'created_at', 'expires_at', 'is_used', 'is_expired_status')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('token', 'created_at', 'expires_at')
    
    def token_short(self, obj):
        return f"{obj.token[:8]}...{obj.token[-8:]}"
    token_short.short_description = 'Token'
    
    def is_expired_status(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">Expiré</span>')
        return format_html('<span style="color: green;">Valide</span>')
    is_expired_status.short_description = 'Statut'

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token_short', 'created_at', 'expires_at', 'is_used', 'is_expired_status')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('token', 'created_at', 'expires_at')
    
    def token_short(self, obj):
        return f"{obj.token[:8]}...{obj.token[-8:]}"
    token_short.short_description = 'Token'
    
    def is_expired_status(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">Expiré</span>')
        return format_html('<span style="color: green;">Valide</span>')
    is_expired_status.short_description = 'Statut'