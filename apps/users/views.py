# apps/users/views.py - Authentification et profils
import json
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView
from django.contrib import messages
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.paginator import Paginator

from apps.users.forms import GestionnaireCreationForm, ProfilUtilisateurForm, ReceptionnisteCreationForm
from apps.users.models import User

def is_gestionnaire(user):
    """Vérifier si l'utilisateur est gestionnaire ou super admin"""
    return user.is_authenticated and user.profil in ['gestionnaire', 'super_admin']

def is_super_admin(user):
    """Vérifier si l'utilisateur est super admin"""
    return user.is_authenticated and user.profil == 'super_admin'

def is_receptionniste(user):
    """Vérifier si l'utilisateur est réceptionniste (ou niveau supérieur)"""
    return user.is_authenticated and user.profil in ['receptionniste', 'gestionnaire', 'super_admin']

class DashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Dashboard principal selon cahier des charges avec activité récente
    Redirige les réceptionnistes vers leur dashboard simplifié
    """
    template_name = 'dashboard/index.html'

    def test_func(self):
        # Autoriser tous les utilisateurs authentifiés (gestionnaire, super_admin, réceptionniste)
        return self.request.user.is_authenticated

    def dispatch(self, request, *args, **kwargs):
        # Rediriger les réceptionnistes vers leur dashboard simplifié
        if request.user.profil == 'receptionniste':
            return redirect('users:dashboard_receptionniste')
        # Les gestionnaires et super_admin continuent vers le dashboard complet
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Importer les modèles ici pour éviter les imports circulaires
        from apps.appartements.models import Appartement
        from apps.clients.models import Client
        from apps.reservations.models import Reservation
        from apps.paiements.models import EcheancierPaiement
        from apps.inventaire.models import EquipementAppartement
        from apps.menage.models import TacheMenage
        
        now = timezone.now()
        today = now.date()
        premier_mois = today.replace(day=1)
        
        # KPIs principaux selon cahier
        context.update({
            # Appartements
            'total_appartements': Appartement.objects.count(),
            'appartements_disponibles': Appartement.objects.filter(statut='disponible').count(),
            'appartements_occupes': Appartement.objects.filter(statut='occupe').count(),
            'appartements_maintenance': Appartement.objects.filter(statut='maintenance').count(),
            
            # Clients
            'total_clients': Client.objects.count(),
            'nouveaux_clients_mois': Client.objects.filter(date_creation__gte=premier_mois).count(),
            
            # Réservations
            'reservations_actives': Reservation.objects.filter(
                statut__in=['confirmee', 'en_cours'],
                date_arrivee__lte=today,
                date_depart__gt=today
            ).count(),
            'reservations_ce_mois': Reservation.objects.filter(
                date_arrivee__year=today.year,
                date_arrivee__month=today.month
            ).count(),
            'reservations_aujourd_hui': Reservation.objects.filter(date_arrivee=today).count(),
            'arrivees_aujourd_hui': Reservation.objects.filter(date_arrivee=today),
            
            # Paiements
            'paiements_en_attente': EcheancierPaiement.objects.filter(statut='en_attente').count(),
            'paiements_retard': EcheancierPaiement.objects.filter(
                statut='en_attente',
                date_echeance__lt=today
            ).count(),
            
            # Inventaire
            'total_equipements': EquipementAppartement.objects.count(),
            'equipements_defectueux': EquipementAppartement.objects.filter(
                etat__in=['defectueux', 'hors_service']
            ).count(),
            
            # Ménage
            'taches_menage_urgentes': TacheMenage.objects.filter(
                statut='a_faire',
                date_prevue__lte=today
            ).count(),
            
            # Calculs financiers simples selon cahier
            'revenus_mois': self.get_revenus_mois(today.year, today.month),
            'taux_occupation': self.get_taux_occupation_mois(today.year, today.month),
            
            # Métadonnées
            'mois_actuel': today,
        })
        
        # Actions récentes pour le dashboard (8 dernières actions)
        try:
            from .models import ActionLog
            actions_recentes = ActionLog.objects.select_related('utilisateur').order_by('-timestamp')[:8]
            context['actions_recentes'] = actions_recentes
        except ImportError:
            # Si le modèle ActionLog n'existe pas encore
            context['actions_recentes'] = []
        
        # Stats spécifiques aux Super Admin
        if self.request.user.profil == 'super_admin':
            context.update({
                'total_gestionnaires': User.objects.filter(profil='gestionnaire').count(),
                'gestionnaires_actifs': User.objects.filter(
                    profil='gestionnaire',
                    is_active=True
                ).count(),
                'super_admins': User.objects.filter(profil='super_admin').count(),
                'total_receptionistes': User.objects.filter(profil='receptionniste').count(),
                'receptionistes_actifs': User.objects.filter(
                    profil='receptionniste',
                    is_active=True
                ).count(),
            })
        
        # Données pour le graphique des revenus (exemple)
        jours_semaine, revenus_semaine = self.get_revenus_7_jours()
        context.update({
            'jours_semaine': json.dumps(jours_semaine),
            'revenus_semaine': json.dumps(revenus_semaine),
        })
        return context
    
    def get_revenus_mois(self, annee, mois):
        """Calcul simple des revenus selon cahier"""
        try:
            from apps.comptabilite.models import ComptabiliteAppartement
            revenus = ComptabiliteAppartement.objects.filter(
                type_mouvement='revenu',
                date_mouvement__year=annee,
                date_mouvement__month=mois
            ).aggregate(total=Sum('montant'))['total']
            return float(revenus) if revenus else 0.0
        except ImportError:
            # Si le modèle n'existe pas encore, calculer à partir des réservations
            from apps.reservations.models import Reservation
            reservations = Reservation.objects.filter(
                statut__in=['confirmee', 'en_cours', 'terminee'],
                date_arrivee__year=annee,
                date_arrivee__month=mois
            ).aggregate(total=Sum('prix_total'))['total']
            return float(reservations) if reservations else 0.0
    
    def get_taux_occupation_mois(self, annee, mois):
        """Calcul simple du taux d'occupation selon cahier"""
        from apps.appartements.models import Appartement
        from apps.reservations.models import Reservation
        from calendar import monthrange
        
        total_appartements = Appartement.objects.count()
        if total_appartements == 0:
            return 0
            
        jours_mois = monthrange(annee, mois)[1]
        nuits_totales_possibles = total_appartements * jours_mois
        
        # Compter les nuits réellement occupées
        nuits_occupees = 0
        for reservation in Reservation.objects.filter(
            statut__in=['confirmee', 'en_cours', 'terminee'],
            date_arrivee__year=annee,
            date_arrivee__month=mois
        ):
            # Intersection avec le mois
            debut_mois = datetime(annee, mois, 1).date()
            fin_mois = datetime(annee, mois, jours_mois).date()
            
            debut_sejour = max(reservation.date_arrivee, debut_mois)
            fin_sejour = min(reservation.date_depart, fin_mois)
            
            if debut_sejour < fin_sejour:
                nuits_occupees += (fin_sejour - debut_sejour).days
        
        return round((nuits_occupees / nuits_totales_possibles) * 100) if nuits_totales_possibles > 0 else 0
    
    def get_revenus_7_jours(self):
        """Calcul des revenus réels des 7 derniers jours"""
        from apps.paiements.models import EcheancierPaiement
        from datetime import timedelta
        
        today = timezone.now().date()
        jours = []
        revenus = []
        
        for i in range(7):
            jour = today - timedelta(days=6-i)
            jours.append(jour.strftime('%d/%m'))
            
            # Revenus du jour
            revenus_jour = EcheancierPaiement.objects.filter(
                statut='paye',
                date_paiement=jour
            ).aggregate(total=Sum('montant_paye'))['total'] or 0
            
            revenus.append(float(revenus_jour))
        
        return jours, revenus


class DashboardReceptionnisteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Dashboard simplifié pour les réceptionnistes
    Affiche uniquement les informations essentielles : arrivées, départs, dernières réservations
    """
    template_name = 'dashboard/receptionniste.html'

    def test_func(self):
        return is_receptionniste(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Importer les modèles
        from apps.appartements.models import Appartement
        from apps.clients.models import Client
        from apps.reservations.models import Reservation

        now = timezone.now()
        today = now.date()

        # Informations de base pour le réceptionniste
        context.update({
            # Statistiques simples
            'total_appartements': Appartement.objects.count(),
            'appartements_disponibles': Appartement.objects.filter(statut='disponible').count(),
            'total_clients': Client.objects.count(),

            # Arrivées et départs du jour
            'arrivees_aujourd_hui': Reservation.objects.filter(
                date_arrivee=today,
                statut='confirmee'
            ).select_related('client', 'appartement'),
            'departs_aujourd_hui': Reservation.objects.filter(
                date_depart=today,
                statut='en_cours'
            ).select_related('client', 'appartement'),

            # Dernières réservations créées
            'dernieres_reservations': Reservation.objects.select_related(
                'client', 'appartement'
            ).order_by('-date_creation')[:5],

            # Métadonnées
            'date_jour': today,
        })

        return context


@login_required
@user_passes_test(is_gestionnaire)
def historique_activites(request):
    """Historique des activités selon cahier"""
    from apps.reservations.models import Reservation
    
    # Récupérer les réservations récentes (dernières 50)
    reservations = Reservation.objects.select_related(
        'client', 'appartement'
    ).order_by('-date_creation')[:50]
    
    # Stats du jour
    today = timezone.now().date()
    stats_jour = {
        'reservations_aujourd_hui': Reservation.objects.filter(date_creation__date=today).count(),
        'paiements_aujourd_hui': 0,  # À implémenter avec le modèle Paiement
        'nouveaux_clients_aujourd_hui': 0,  # À implémenter avec le modèle Client
    }
    
    context = {
        'reservations': reservations,
        **stats_jour,
    }
    return render(request, 'users/historique.html', context)


class ListeGestionnairesView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Liste des gestionnaires - Réservé au Super Admin selon cahier
    """
    model = User
    template_name = 'users/liste_gestionnaires.html'
    context_object_name = 'gestionnaires'
    paginate_by = 20
    
    def test_func(self):
        return is_super_admin(self.request.user)
    
    def get_queryset(self):
        """Filtrer les utilisateurs par profil et recherche"""
        queryset = User.objects.filter(
            profil__in=['gestionnaire', 'super_admin']
        ).order_by('-date_joined')
        
        # Recherche
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        # Filtrer par statut
        statut = self.request.GET.get('statut', '')
        if statut == 'actif':
            queryset = queryset.filter(is_active=True)
        elif statut == 'inactif':
            queryset = queryset.filter(is_active=False)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Stats des gestionnaires
        context.update({
            'total_gestionnaires': User.objects.filter(profil='gestionnaire').count(),
            'gestionnaires_actifs': User.objects.filter(profil='gestionnaire', is_active=True).count(),
            'gestionnaires_inactifs': User.objects.filter(profil='gestionnaire', is_active=False).count(),  # Ajoutez cette ligne
            'super_admins': User.objects.filter(profil='super_admin').count(),
        })        
        return context


@login_required
@user_passes_test(is_super_admin)
def creer_gestionnaire(request):
    """Créer un gestionnaire selon cahier"""
    if request.method == 'POST':
        form = GestionnaireCreationForm(request.POST)
        if form.is_valid():
            gestionnaire = form.save(commit=False)
            gestionnaire.set_password(form.cleaned_data['password1'])
            gestionnaire.save()
            
            messages.success(
                request, 
                f'Gestionnaire {gestionnaire.username} créé avec succès ! '
                f'Il peut maintenant se connecter au système.'
            )
            return redirect('users:liste_gestionnaires')
    else:
        form = GestionnaireCreationForm()
    
    context = {
        'form': form,
        'titre': 'Créer un gestionnaire',
    }
    return render(request, 'users/creer_gestionnaire.html', context)


@login_required
@user_passes_test(is_super_admin)
def modifier_gestionnaire(request, pk):
    """Modifier un gestionnaire selon cahier"""                 
    gestionnaire = get_object_or_404(User, pk=pk)
    
    # Vérifier que c'est bien un gestionnaire ou super admin
    if gestionnaire.profil not in ['gestionnaire', 'super_admin']:
        messages.error(request, "Cet utilisateur n'est pas un gestionnaire.")
        return redirect('users:liste_gestionnaires')
    
    if request.method == 'POST':
        form = GestionnaireCreationForm(request.POST, instance=gestionnaire)
        if form.is_valid():
            gestionnaire = form.save(commit=False)
            
            # Changer le mot de passe seulement s'il est fourni
            if form.cleaned_data.get('password1'):
                gestionnaire.set_password(form.cleaned_data['password1'])
            
            gestionnaire.save()
            
            messages.success(
                request, 
                f'Gestionnaire {gestionnaire.username} modifié avec succès !'
            )
            return redirect('users:liste_gestionnaires')
    else:
        # Pré-remplir le formulaire avec les données existantes
        form = GestionnaireCreationForm(instance=gestionnaire)
        # Vider les champs de mot de passe pour la modification
        form.fields['password1'].required = False
        form.fields['password2'].required = False
    
    context = {
        'form': form,
        'gestionnaire': gestionnaire,
        'titre': f'Modifier {gestionnaire.username}',
    }
    return render(request, 'users/modifier_gestionnaire.html', context)


@login_required
@user_passes_test(is_super_admin)
def desactiver_gestionnaire(request, pk):
    """Désactiver un gestionnaire selon cahier"""
    gestionnaire = get_object_or_404(User, pk=pk)
    
    # Empêcher la désactivation de son propre compte
    if gestionnaire == request.user:
        messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
        return redirect('users:liste_gestionnaires')
    
    # Vérifier que c'est bien un gestionnaire
    if gestionnaire.profil not in ['gestionnaire', 'super_admin']:
        messages.error(request, "Cet utilisateur n'est pas un gestionnaire.")
        return redirect('users:liste_gestionnaires')
    
    if request.method == 'POST':
        gestionnaire.is_active = False
        gestionnaire.save()
        
        messages.success(
            request, 
            f'Gestionnaire {gestionnaire.username} désactivé avec succès ! '
            f'Il ne peut plus se connecter au système.'
        )
        return redirect('users:liste_gestionnaires')
    
    context = {
        'gestionnaire': gestionnaire,
        'titre': f'Désactiver {gestionnaire.username}',
    }
    return render(request, 'users/desactiver_gestionnaire.html', context)


@login_required
@user_passes_test(is_super_admin)
def reactiver_gestionnaire(request, pk):
    """Réactiver un gestionnaire désactivé"""
    gestionnaire = get_object_or_404(User, pk=pk)
    
    if gestionnaire.is_active:
        messages.info(request, f"Le gestionnaire {gestionnaire.username} est déjà actif.")
    else:
        gestionnaire.is_active = True
        gestionnaire.save()
        
        messages.success(
            request, 
            f'Gestionnaire {gestionnaire.username} réactivé avec succès ! '
            f'Il peut maintenant se reconnecter au système.'
        )
    
    return redirect('users:liste_gestionnaires')


@login_required
@user_passes_test(is_gestionnaire)
def profil_utilisateur(request):
    """Profil utilisateur selon cahier"""
    if request.method == 'POST':
        form = ProfilUtilisateurForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            
            messages.success(
                request, 
                'Votre profil a été mis à jour avec succès !'
            )
            return redirect('users:profil')
    else:
        form = ProfilUtilisateurForm(instance=request.user)
    
    context = {
        'form': form,
        'titre': 'Mon Profil',
    }
    return render(request, 'users/profil_utilisateur.html', context)

@login_required
@user_passes_test(is_super_admin)
def journal_actions(request):
    """Journal des actions - Admin seulement"""
    from .models import ActionLog
    
    # Filtres
    action_filter = request.GET.get('action', '')
    model_filter = request.GET.get('model', '')
    user_filter = request.GET.get('user', '')
    
    logs = ActionLog.objects.select_related('utilisateur').order_by('-timestamp')
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    if model_filter:
        logs = logs.filter(model_name__icontains=model_filter)
    if user_filter:
        logs = logs.filter(utilisateur__username__icontains=user_filter)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    
    context = {
        'logs': logs_page,
        'action_filter': action_filter,
        'model_filter': model_filter,
        'user_filter': user_filter,
        'action_choices': ActionLog.ACTION_CHOICES,
    }
    return render(request, 'users/journal_actions.html', context)

@login_required  
@user_passes_test(is_super_admin)
def statistiques_audit(request):
    """Statistiques d'audit"""
    from .models import ActionLog
    from django.db.models import Count
    from datetime import timedelta
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    stats = {
        'total_actions': ActionLog.objects.count(),
        'actions_today': ActionLog.objects.filter(timestamp__date=today).count(),
        'actions_week': ActionLog.objects.filter(timestamp__date__gte=week_ago).count(),
        'actions_month': ActionLog.objects.filter(timestamp__date__gte=month_ago).count(),
        'actions_by_type': ActionLog.objects.values('action').annotate(count=Count('action')),
        'actions_by_user': ActionLog.objects.filter(
            utilisateur__isnull=False
        ).values('utilisateur__username').annotate(count=Count('utilisateur')).order_by('-count')[:10],
        'actions_by_model': ActionLog.objects.values('model_name').annotate(count=Count('model_name')).order_by('-count')[:10],
    }
    
    return render(request, 'users/statistiques_audit.html', {'stats': stats})


# ==========================================
# Gestion des réceptionnistes (Super Admin uniquement)
# ==========================================

@login_required
@user_passes_test(is_super_admin)
def liste_receptionistes(request):
    """Liste des réceptionnistes - Réservé au Super Admin"""
    # Filtrer les utilisateurs réceptionnistes
    receptionistes = User.objects.filter(profil='receptionniste').order_by('-date_joined')

    # Recherche
    search = request.GET.get('search', '').strip()
    if search:
        receptionistes = receptionistes.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    # Filtrer par statut
    statut = request.GET.get('statut', '')
    if statut == 'actif':
        receptionistes = receptionistes.filter(is_active=True)
    elif statut == 'inactif':
        receptionistes = receptionistes.filter(is_active=False)

    # Pagination
    paginator = Paginator(receptionistes, 20)
    page = request.GET.get('page')
    receptionistes_page = paginator.get_page(page)

    context = {
        'receptionistes': receptionistes_page,
        'total_receptionistes': User.objects.filter(profil='receptionniste').count(),
        'receptionistes_actifs': User.objects.filter(profil='receptionniste', is_active=True).count(),
        'receptionistes_inactifs': User.objects.filter(profil='receptionniste', is_active=False).count(),
    }
    return render(request, 'users/liste_receptionistes.html', context)


@login_required
@user_passes_test(is_super_admin)
def creer_receptionniste(request):
    """Créer un réceptionniste - Réservé au Super Admin"""
    if request.method == 'POST':
        form = ReceptionnisteCreationForm(request.POST)
        if form.is_valid():
            receptionniste = form.save(commit=False)
            receptionniste.set_password(form.cleaned_data['password1'])
            receptionniste.save()

            messages.success(
                request,
                f'Réceptionniste {receptionniste.username} créé avec succès ! '
                f'Il peut maintenant se connecter au système.'
            )
            return redirect('users:liste_receptionistes')
    else:
        form = ReceptionnisteCreationForm()

    context = {
        'form': form,
        'titre': 'Créer un réceptionniste',
    }
    return render(request, 'users/creer_receptionniste.html', context)


@login_required
@user_passes_test(is_super_admin)
def modifier_receptionniste(request, pk):
    """Modifier un réceptionniste - Réservé au Super Admin"""
    receptionniste = get_object_or_404(User, pk=pk)

    # Vérifier que c'est bien un réceptionniste
    if receptionniste.profil != 'receptionniste':
        messages.error(request, "Cet utilisateur n'est pas un réceptionniste.")
        return redirect('users:liste_receptionistes')

    if request.method == 'POST':
        form = ReceptionnisteCreationForm(request.POST, instance=receptionniste)
        if form.is_valid():
            receptionniste = form.save(commit=False)

            # Changer le mot de passe seulement s'il est fourni
            if form.cleaned_data.get('password1'):
                receptionniste.set_password(form.cleaned_data['password1'])

            receptionniste.save()

            messages.success(
                request,
                f'Réceptionniste {receptionniste.username} modifié avec succès !'
            )
            return redirect('users:liste_receptionistes')
    else:
        # Pré-remplir le formulaire avec les données existantes
        form = ReceptionnisteCreationForm(instance=receptionniste)
        # Vider les champs de mot de passe pour la modification
        form.fields['password1'].required = False
        form.fields['password2'].required = False

    context = {
        'form': form,
        'receptionniste': receptionniste,
        'titre': f'Modifier {receptionniste.username}',
    }
    return render(request, 'users/modifier_receptionniste.html', context)


@login_required
@user_passes_test(is_super_admin)
def desactiver_receptionniste(request, pk):
    """Désactiver un réceptionniste - Réservé au Super Admin"""
    receptionniste = get_object_or_404(User, pk=pk)

    # Vérifier que c'est bien un réceptionniste
    if receptionniste.profil != 'receptionniste':
        messages.error(request, "Cet utilisateur n'est pas un réceptionniste.")
        return redirect('users:liste_receptionistes')

    if request.method == 'POST':
        receptionniste.is_active = False
        receptionniste.save()

        messages.success(
            request,
            f'Réceptionniste {receptionniste.username} désactivé avec succès ! '
            f'Il ne peut plus se connecter au système.'
        )
        return redirect('users:liste_receptionistes')

    context = {
        'receptionniste': receptionniste,
        'titre': f'Désactiver {receptionniste.username}',
    }
    return render(request, 'users/desactiver_receptionniste.html', context)


@login_required
@user_passes_test(is_super_admin)
def reactiver_receptionniste(request, pk):
    """Réactiver un réceptionniste désactivé - Réservé au Super Admin"""
    receptionniste = get_object_or_404(User, pk=pk)

    if receptionniste.is_active:
        messages.info(request, f"Le réceptionniste {receptionniste.username} est déjà actif.")
    else:
        receptionniste.is_active = True
        receptionniste.save()

        messages.success(
            request,
            f'Réceptionniste {receptionniste.username} réactivé avec succès ! '
            f'Il peut maintenant se reconnecter au système.'
        )

    return redirect('users:liste_receptionistes')