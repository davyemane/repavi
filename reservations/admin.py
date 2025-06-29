# reservations/admin.py - Interface d'administration pour les réservations

from django.contrib import admin
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import (
    TypePaiement, Reservation, Paiement, 
    EvaluationReservation, Disponibilite
)


@admin.register(TypePaiement)
class TypePaiementAdmin(admin.ModelAdmin):
    """Administration des types de paiement"""
    list_display = [
        'nom', 'frais_pourcentage', 'frais_fixe', 'actif', 
        'exemple_frais', 'date_creation'
    ]
    list_filter = ['actif', 'date_creation']
    search_fields = ['nom', 'description']
    readonly_fields = ['date_creation', 'date_modification']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'description', 'actif')
        }),
        ('Configuration des frais', {
            'fields': ('frais_pourcentage', 'frais_fixe')
        }),
        ('Apparence', {
            'fields': ('icone', 'couleur')
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    def exemple_frais(self, obj):
        """Affiche un exemple de frais pour 100 000 FCFA"""
        frais = obj.frais_total_exemple
        return f"{frais:,.0f} FCFA"
    exemple_frais.short_description = "Frais pour 100k FCFA"


class PaiementInline(admin.TabularInline):
    """Inline pour les paiements"""
    model = Paiement
    extra = 0
    readonly_fields = ['numero_transaction', 'montant_net', 'date_creation', 'date_validation']
    fields = [
        'type_paiement', 'montant', 'frais', 'montant_net', 
        'statut', 'reference_externe', 'date_creation'
    ]
    
    def has_delete_permission(self, request, obj=None):
        return False


class EvaluationInline(admin.StackedInline):
    """Inline pour l'évaluation"""
    model = EvaluationReservation
    extra = 0
    readonly_fields = ['date_creation', 'date_reponse_gestionnaire']
    fields = [
        'note_globale', 'note_proprete', 'note_equipements',
        'note_emplacement', 'note_rapport_qualite_prix',
        'commentaire', 'recommande', 'reviendrait',
        'approuve', 'reponse_gestionnaire', 'date_reponse_gestionnaire'
    ]


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """Administration des réservations"""
    list_display = [
        'numero', 'client_info', 'maison_info', 'periode_sejour',
        'statut_badge', 'prix_total', 'mode_paiement', 'date_creation'
    ]
    list_filter = [
        'statut', 'mode_paiement', 'date_creation', 'date_debut',
        'maison__ville', 'maison__categorie'
    ]
    search_fields = [
        'numero', 'client__first_name', 'client__last_name', 
        'client__email', 'maison__nom', 'maison__numero'
    ]
    readonly_fields = [
        'numero', 'nombre_nuits', 'sous_total', 'prix_total',
        'date_creation', 'date_modification', 'ip_creation'
    ]
    
    date_hierarchy = 'date_creation'
    
    fieldsets = (
        ('Informations principales', {
            'fields': (
                'numero', 'client', 'maison', 'statut'
            )
        }),
        ('Période et détails du séjour', {
            'fields': (
                'date_debut', 'date_fin', 'nombre_nuits',
                'heure_arrivee', 'heure_depart', 'nombre_personnes'
            )
        }),
        ('Tarification', {
            'fields': (
                'prix_par_nuit', 'sous_total', 'frais_service',
                'reduction_montant', 'reduction_raison', 'prix_total'
            )
        }),
        ('Paiement', {
            'fields': (
                'mode_paiement', 'montant_acompte'
            )
        }),
        ('Commentaires', {
            'fields': (
                'commentaire_client', 'commentaire_gestionnaire'
            )
        }),
        ('Contact d\'urgence', {
            'fields': (
                'contact_urgence_nom', 'contact_urgence_telephone'
            ),
            'classes': ('collapse',)
        }),
        ('Annulation', {
            'fields': (
                'date_annulation', 'raison_annulation', 'annulee_par'
            ),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': (
                'date_creation', 'date_modification', 'ip_creation', 'user_agent'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PaiementInline, EvaluationInline]
    
    actions = ['confirmer_reservations', 'exporter_selection']
    
    def client_info(self, obj):
        """Informations du client avec lien"""
        url = reverse('admin:auth_user_change', args=[obj.client.pk])
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            url, obj.client.get_full_name(), obj.client.email
        )
    client_info.short_description = "Client"
    
    def maison_info(self, obj):
        """Informations de la maison avec lien"""
        url = reverse('admin:home_maison_change', args=[obj.maison.pk])
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            url, obj.maison.nom, obj.maison.ville.nom
        )
    maison_info.short_description = "Maison"
    
    def periode_sejour(self, obj):
        """Période du séjour formatée"""
        return format_html(
            '{} au {}<br><small>{} nuit{}</small>',
            obj.date_debut.strftime('%d/%m/%Y'),
            obj.date_fin.strftime('%d/%m/%Y'),
            obj.nombre_nuits,
            's' if obj.nombre_nuits > 1 else ''
        )
    periode_sejour.short_description = "Période"
    
    def statut_badge(self, obj):
        """Statut avec badge coloré"""
        colors = {
            'en_attente': 'orange',
            'confirmee': 'green',
            'terminee': 'blue',
            'annulee': 'red'
        }
        color = colors.get(obj.statut, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_statut_display()
        )
    statut_badge.short_description = "Statut"
    
    def confirmer_reservations(self, request, queryset):
        """Action pour confirmer plusieurs réservations"""
        count = 0
        for reservation in queryset.filter(statut='en_attente'):
            try:
                reservation.confirmer()
                count += 1
            except:
                pass
        
        self.message_user(
            request, 
            f"{count} réservation(s) confirmée(s) avec succès."
        )
    confirmer_reservations.short_description = "Confirmer les réservations sélectionnées"
    
    def exporter_selection(self, request, queryset):
        """Action d'export (placeholder)"""
        self.message_user(
            request,
            f"{queryset.count()} réservations sélectionnées pour export."
        )
    exporter_selection.short_description = "Exporter la sélection"
    
    def get_queryset(self, request):
        """Optimiser les requêtes"""
        return super().get_queryset(request).select_related(
            'client', 'maison', 'maison__ville', 'annulee_par'
        ).prefetch_related('paiements')
    
    def changelist_view(self, request, extra_context=None):
        """Ajouter des statistiques à la vue liste"""
        # Statistiques rapides
        response = super().changelist_view(request, extra_context=extra_context)
        
        try:
            qs = response.context_data['cl'].queryset
            
            stats = {
                'total_reservations': qs.count(),
                'en_attente': qs.filter(statut='en_attente').count(),
                'confirmees': qs.filter(statut='confirmee').count(),
                'ca_total': qs.filter(
                    statut__in=['confirmee', 'terminee']
                ).aggregate(total=Sum('prix_total'))['total'] or 0,
                'arrivees_aujourdhui': qs.filter(
                    statut='confirmee',
                    date_debut=timezone.now().date()
                ).count(),
            }
            
            response.context_data['stats'] = stats
        except (AttributeError, KeyError):
            pass
        
        return response


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    """Administration des paiements"""
    list_display = [
        'numero_transaction', 'reservation_link', 'montant',
        'statut_badge', 'type_paiement', 'date_creation'
    ]
    list_filter = [
        'statut', 'type_paiement', 'date_creation',
        'reservation__maison__gestionnaire'
    ]
    search_fields = [
        'numero_transaction', 'reference_externe',
        'reservation__numero', 'reservation__client__email'
    ]
    readonly_fields = [
        'numero_transaction', 'montant_net', 'date_creation',
        'date_validation', 'date_echec'
    ]
    
    fieldsets = (
        ('Informations générales', {
            'fields': (
                'reservation', 'type_paiement', 'numero_transaction'
            )
        }),
        ('Montants', {
            'fields': (
                'montant', 'frais', 'montant_net'
            )
        }),
        ('Statut et références', {
            'fields': (
                'statut', 'reference_externe', 'notes'
            )
        }),
        ('Dates', {
            'fields': (
                'date_creation', 'date_validation', 'date_echec'
            )
        }),
        ('Données techniques', {
            'fields': ('reponse_gateway',),
            'classes': ('collapse',)
        }),
    )
    
    def reservation_link(self, obj):
        """Lien vers la réservation"""
        url = reverse('admin:reservations_reservation_change', args=[obj.reservation.pk])
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.reservation.numero
        )
    reservation_link.short_description = "Réservation"
    
    def statut_badge(self, obj):
        """Statut avec badge coloré"""
        colors = {
            'en_attente': 'orange',
            'valide': 'green',
            'echec': 'red',
            'rembourse': 'blue'
        }
        color = colors.get(obj.statut, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_statut_display()
        )
    statut_badge.short_description = "Statut"


@admin.register(EvaluationReservation)
class EvaluationReservationAdmin(admin.ModelAdmin):
    """Administration des évaluations"""
    list_display = [
        'reservation_info', 'note_globale_stars', 'recommande',
        'approuve', 'a_reponse', 'date_creation'
    ]
    list_filter = [
        'note_globale', 'recommande', 'reviendrait', 'approuve',
        'date_creation'
    ]
    search_fields = [
        'reservation__numero', 'reservation__client__email',
        'commentaire', 'reponse_gestionnaire'
    ]
    readonly_fields = ['date_creation', 'date_modification', 'note_moyenne_calculee']
    
    fieldsets = (
        ('Réservation', {
            'fields': ('reservation',)
        }),
        ('Notes (1-5 étoiles)', {
            'fields': (
                'note_globale', 'note_proprete', 'note_equipements',
                'note_emplacement', 'note_rapport_qualite_prix', 'note_moyenne_calculee'
            )
        }),
        ('Commentaires', {
            'fields': (
                'commentaire', 'points_positifs', 'points_amelioration'
            )
        }),
        ('Recommandations', {
            'fields': ('recommande', 'reviendrait')
        }),
        ('Modération', {
            'fields': ('approuve', 'raison_rejet')
        }),
        ('Réponse du gestionnaire', {
            'fields': (
                'reponse_gestionnaire', 'date_reponse_gestionnaire'
            )
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    def reservation_info(self, obj):
        """Informations de la réservation"""
        url = reverse('admin:reservations_reservation_change', args=[obj.reservation.pk])
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            url, obj.reservation.numero, obj.reservation.maison.nom
        )
    reservation_info.short_description = "Réservation"
    
    def note_globale_stars(self, obj):
        """Affichage des étoiles pour la note globale"""
        stars = '★' * obj.note_globale + '☆' * (5 - obj.note_globale)
        return format_html(
            '<span style="color: gold; font-size: 16px;">{}</span> ({})',
            stars, obj.note_globale
        )
    note_globale_stars.short_description = "Note globale"
    
    def a_reponse(self, obj):
        """Indique s'il y a une réponse du gestionnaire"""
        if obj.reponse_gestionnaire:
            return format_html(
                '<span style="color: green;">✓</span>'
            )
        return format_html(
            '<span style="color: red;">✗</span>'
        )
    a_reponse.short_description = "Réponse"
    a_reponse.boolean = True
    
    def note_moyenne_calculee(self, obj):
        """Note moyenne calculée"""
        return f"{obj.note_moyenne:.1f}/5"
    note_moyenne_calculee.short_description = "Moyenne"


@admin.register(Disponibilite)
class DisponibiliteAdmin(admin.ModelAdmin):
    """Administration des disponibilités"""
    list_display = [
        'maison', 'date', 'disponible_badge', 'prix_effectif_display',
        'raison_indisponibilite'
    ]
    list_filter = [
        'disponible', 'date', 'maison__gestionnaire', 'maison__ville'
    ]
    search_fields = [
        'maison__nom', 'maison__numero', 'raison_indisponibilite'
    ]
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('maison', 'date', 'disponible')
        }),
        ('Tarification', {
            'fields': ('prix_special',)
        }),
        ('Indisponibilité', {
            'fields': ('raison_indisponibilite',)
        }),
    )
    
    def disponible_badge(self, obj):
        """Badge pour la disponibilité"""
        if obj.disponible:
            return format_html(
                '<span style="background-color: green; color: white; '
                'padding: 2px 6px; border-radius: 3px;">Disponible</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; '
                'padding: 2px 6px; border-radius: 3px;">Indisponible</span>'
            )
    disponible_badge.short_description = "Disponibilité"
    
    def prix_effectif_display(self, obj):
        """Prix effectif avec indication du prix spécial"""
        prix = obj.prix_effectif
        if obj.prix_special:
            return format_html(
                '<strong>{:,.0f} FCFA</strong> <small>(spécial)</small>',
                prix
            )
        return f"{prix:,.0f} FCFA"
    prix_effectif_display.short_description = "Prix"
    
    def get_queryset(self, request):
        """Optimiser les requêtes"""
        return super().get_queryset(request).select_related('maison')


# Configuration de l'admin site
admin.site.site_header = "RepAvi Lodges - Administration"
admin.site.site_title = "RepAvi Admin"
admin.site.index_title = "Gestion des réservations"