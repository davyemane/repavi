# apps/users/views.py - Authentification et profils
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView
from django.contrib import messages
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.paginator import Paginator

from apps.users.forms import GestionnaireCreationForm, ProfilUtilisateurForm
from apps.users.models import User

def is_gestionnaire(user):
    """Vérifier si l'utilisateur est gestionnaire ou super admin"""
    return user.is_authenticated and user.profil in ['gestionnaire', 'super_admin']

def is_super_admin(user):
    """Vérifier si l'utilisateur est super admin"""
    return user.is_authenticated and user.profil == 'super_admin'

class DashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Dashboard principal selon cahier des charges
    """
    template_name = 'dashboard/index.html'
    
    def test_func(self):
        return is_gestionnaire(self.request.user)
    
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
        
        # Stats spécifiques aux Super Admin
        if self.request.user.profil == 'super_admin':
            context.update({
                'total_gestionnaires': User.objects.filter(profil='gestionnaire').count(),
                'gestionnaires_actifs': User.objects.filter(
                    profil='gestionnaire', 
                    is_active=True
                ).count(),
                'super_admins': User.objects.filter(profil='super_admin').count(),
            })
        
        # Données pour le graphique des revenus (exemple)
        context.update({
            'jours_semaine': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
            'revenus_semaine': [45000, 52000, 38000, 67000, 89000, 125000, 98000],  # À calculer dynamiquement
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
            ).aggregate(total=Sum('montant_total'))['total']
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