# avis/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .models import Avis, PhotoAvis, LikeAvis, SignalementAvis
from .forms import (
    AvisForm, PhotoAvisForm, ReponseGestionnaireForm,
    SignalementAvisForm, FiltreAvisForm, ModerationAvisForm, PhotoAvisFormSet
)
from home.models import Maison
from users.models import User


# ============================================================================
# VUES PUBLIQUES - CONSULTATION DES AVIS
# ============================================================================

class AvisListView(ListView):
    """Liste des avis publics d'une maison"""
    model = Avis
    template_name = 'avis/list.html'
    context_object_name = 'avis_list'
    paginate_by = 10
    
    def get_queryset(self):
        self.maison = get_object_or_404(Maison, slug=self.kwargs['slug'])
        queryset = Avis.objects.published().filter(maison=self.maison)
        
        # Appliquer les filtres
        form = FiltreAvisForm(self.request.GET)
        if form.is_valid():
            note_min = form.cleaned_data.get('note_min')
            if note_min:
                queryset = queryset.filter(note__gte=note_min)
            
            if form.cleaned_data.get('avec_photos'):
                queryset = queryset.with_photos()
            
            if form.cleaned_data.get('avec_reponse'):
                queryset = queryset.with_responses()
            
            tri = form.cleaned_data.get('tri', '-date_creation')
            queryset = queryset.order_by(tri)
        
        return queryset.select_related('client', 'reponse_par').prefetch_related('photos', 'likes')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['maison'] = self.maison
        context['filtre_form'] = FiltreAvisForm(self.request.GET)
        
        # Statistiques des avis
        avis_stats = self.maison.avis.filter(statut_moderation='approuve').aggregate(
            note_moyenne=Avg('note'),
            total_avis=Count('id'),
            recommandations=Count('id', filter=Q(recommande=True))
        )
        
        context['avis_stats'] = avis_stats
        context['pourcentage_recommandation'] = self.maison.get_pourcentage_recommandation()
        context['repartition_notes'] = self.maison.get_repartition_notes()
        
        # Vérifier si l'utilisateur peut donner un avis
        if self.request.user.is_authenticated:
            context['peut_donner_avis'] = (
                self.request.user.is_client() and
                not Avis.objects.filter(
                    client=self.request.user, 
                    maison=self.maison
                ).exists()
            )
        
        return context

def avis_detail_ajax(request, avis_id):
    """Détail d'un avis en AJAX pour modal"""
    avis = get_object_or_404(Avis, id=avis_id, statut_moderation='approuve')
    
    data = {
        'id': avis.id,
        'client_nom': avis.client.nom_complet,
        'note': avis.note,
        'note_etoiles': avis.note_etoiles,
        'titre': avis.titre,
        'commentaire': avis.commentaire,
        'date_creation': avis.date_creation.strftime('%d/%m/%Y'),
        'date_sejour': avis.date_sejour.strftime('%d/%m/%Y') if avis.date_sejour else None,
        'duree_sejour': avis.duree_sejour,
        'recommande': avis.recommande,
        'reponse_gestionnaire': avis.reponse_gestionnaire,
        'reponse_par': avis.reponse_par.nom_complet if avis.reponse_par else None,
        'date_reponse': avis.date_reponse.strftime('%d/%m/%Y') if avis.date_reponse else None,
        'nombre_likes': avis.nombre_likes,
        'photos': [
            {
                'url': photo.image.url,
                'legende': photo.legende
            } for photo in avis.photos.all()
        ]
    }
    
    return JsonResponse(data)


# ============================================================================
# VUES CLIENT - CREATION ET GESTION D'AVIS
# ============================================================================

# avis/views.py - Vue CreerAvisView complètement corrigée

@method_decorator(login_required, name='dispatch')
class CreerAvisView(UserPassesTestMixin, CreateView):
    """Créer un nouvel avis"""
    model = Avis
    form_class = AvisForm
    template_name = 'avis/creer_avis.html'
    
    def test_func(self):
        """Seuls les clients peuvent créer des avis"""
        return hasattr(self.request.user, 'is_client') and self.request.user.is_client()
    
    def dispatch(self, request, *args, **kwargs):
        self.maison = get_object_or_404(Maison, slug=kwargs['slug'])
        
        # Vérifier que l'utilisateur n'a pas déjà donné un avis
        if Avis.objects.filter(client=request.user, maison=self.maison).exists():
            messages.error(request, "Vous avez déjà donné un avis pour cette maison.")
            return redirect('avis:avis_list', slug=self.maison.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['maison'] = self.maison
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['maison'] = self.maison
        context['title'] = f'Donner un avis pour {self.maison.nom}'
        
        # Formset pour les photos (optionnel)
        if self.request.POST:
            try:
                context['photo_formset'] = PhotoAvisFormSet(
                    self.request.POST, 
                    self.request.FILES
                )
            except:
                context['photo_formset'] = PhotoAvisFormSet()
        else:
            context['photo_formset'] = PhotoAvisFormSet()
        
        return context
    
    def form_valid(self, form):
        """Sauvegarder l'avis et les photos"""
        try:
            # ASSIGNATION EXPLICITE AVANT TOUTE SAUVEGARDE
            avis = form.save(commit=False)
            avis.client = self.request.user
            avis.maison = self.maison
            
            # Vérification finale
            if not avis.client or not avis.maison:
                messages.error(self.request, "Erreur lors de la création de l'avis.")
                return self.form_invalid(form)
            
            # Sauvegarder l'avis
            avis.save()
            self.object = avis
            
            # Traiter les photos si présentes
            context = self.get_context_data()
            photo_formset = context.get('photo_formset')
            
            if photo_formset and photo_formset.is_valid():
                try:
                    photo_formset.instance = avis
                    photo_formset.save()
                except Exception as e:
                    # Si erreur avec les photos, ne pas faire échouer l'avis
                    print(f"Erreur lors de la sauvegarde des photos: {e}")
            
            messages.success(
                self.request, 
                "Votre avis a été soumis avec succès ! Il sera publié après modération."
            )
            
            return redirect('avis:avis_list', slug=self.maison.slug)
            
        except Exception as e:
            print(f"Erreur lors de la création de l'avis: {e}")
            messages.error(self.request, "Une erreur est survenue lors de la création de votre avis.")
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Gestion des erreurs de formulaire"""
        print("Erreurs du formulaire:", form.errors)
        messages.error(self.request, "Veuillez corriger les erreurs dans le formulaire.")
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse('avis:avis_list', kwargs={'slug': self.maison.slug})

@login_required
def modifier_avis(request, avis_id):
    """Modifier un avis existant (dans les 24h)"""
    avis = get_object_or_404(Avis, id=avis_id, client=request.user)
    
    if not avis.peut_etre_modifie:
        messages.error(request, "Cet avis ne peut plus être modifié.")
        return redirect('avis:avis_list', slug=avis.maison.slug)
    
    if request.method == 'POST':
        form = AvisForm(request.POST, instance=avis)
        photo_formset = PhotoAvisFormSet(
            request.POST, 
            request.FILES, 
            instance=avis
        )
        
        if form.is_valid() and photo_formset.is_valid():
            form.save()
            photo_formset.save()
            
            messages.success(request, "Votre avis a été mis à jour avec succès.")
            return redirect('avis:avis_list', slug=avis.maison.slug)
    else:
        form = AvisForm(instance=avis)
        photo_formset = PhotoAvisFormSet(instance=avis)
    
    context = {
        'form': form,
        'photo_formset': photo_formset,
        'avis': avis,
        'maison': avis.maison
    }
    
    return render(request, 'avis/modifier_avis.html', context)


@login_required
def mes_avis(request):
    """Liste des avis de l'utilisateur connecté"""
    if not request.user.is_client():
        messages.error(request, "Accès non autorisé.")
        return redirect('home:index')
    
    avis_list = Avis.objects.filter(client=request.user).select_related('maison').order_by('-date_creation')
    
    paginator = Paginator(avis_list, 10)
    page_number = request.GET.get('page')
    avis = paginator.get_page(page_number)
    
    context = {
        'avis': avis,
        'title': 'Mes avis'
    }
    
    return render(request, 'avis/mes_avis.html', context)


# ============================================================================
# VUES GESTIONNAIRE - REPONSES ET MODERATION
# ============================================================================

@login_required
def repondre_avis(request, avis_id):
    """Répondre à un avis (gestionnaires uniquement)"""
    avis = get_object_or_404(Avis, id=avis_id, statut_moderation='approuve')
    
    # Vérifier les permissions
    if not (request.user.has_gestionnaire_permissions() and 
            avis.maison.can_be_managed_by(request.user)):
        return HttpResponseForbidden("Vous n'avez pas l'autorisation de répondre à cet avis.")
    
    if request.method == 'POST':
        form = ReponseGestionnaireForm(request.POST, instance=avis, gestionnaire=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre réponse a été publiée avec succès.")
            return redirect('avis:avis_list', slug=avis.maison.slug)
    else:
        form = ReponseGestionnaireForm(instance=avis, gestionnaire=request.user)
    
    context = {
        'form': form,
        'avis': avis,
        'maison': avis.maison
    }
    
    return render(request, 'avis/repondre_avis.html', context)


@login_required
def tableau_avis_gestionnaire(request):
    """Tableau de bord des avis pour gestionnaires"""
    if not request.user.has_gestionnaire_permissions():
        messages.error(request, "Accès non autorisé.")
        return redirect('home:index')
    
    # Filtrer selon le rôle
    if request.user.is_super_admin():
        avis_queryset = Avis.objects.all()
    else:
        avis_queryset = Avis.objects.filter(maison__gestionnaire=request.user)
    
    # Statistiques
    stats = {
        'total_avis': avis_queryset.count(),
        'en_attente': avis_queryset.filter(statut_moderation='en_attente').count(),
        'approuves': avis_queryset.filter(statut_moderation='approuve').count(),
        'signales': avis_queryset.filter(statut_moderation='signale').count(),
        'sans_reponse': avis_queryset.filter(
            statut_moderation='approuve',
            reponse_gestionnaire=''
        ).count()
    }
    
    # Avis récents nécessitant une action
    avis_en_attente = avis_queryset.filter(
        statut_moderation='en_attente'
    ).select_related('client', 'maison').order_by('-date_creation')[:10]
    
    avis_sans_reponse = avis_queryset.filter(
        statut_moderation='approuve',
        reponse_gestionnaire=''
    ).select_related('client', 'maison').order_by('-date_creation')[:10]
    
    context = {
        'stats': stats,
        'avis_en_attente': avis_en_attente,
        'avis_sans_reponse': avis_sans_reponse,
        'title': 'Gestion des avis'
    }
    
    return render(request, 'avis/tableau_avis_gestionnaire.html', context)


@login_required
def moderer_avis(request, avis_id):
    """Modérer un avis (approuver/rejeter)"""
    avis = get_object_or_404(Avis, id=avis_id)
    
    # Vérifier les permissions
    if not (request.user.has_gestionnaire_permissions() and 
            (request.user.is_super_admin() or 
             avis.maison.can_be_managed_by(request.user))):
        return HttpResponseForbidden("Vous n'avez pas l'autorisation de modérer cet avis.")
    
    if request.method == 'POST':
        form = ModerationAvisForm(request.POST, instance=avis, moderateur=request.user)
        if form.is_valid():
            form.save()
            
            statut = form.cleaned_data['statut_moderation']
            if statut == 'approuve':
                messages.success(request, "L'avis a été approuvé et publié.")
            elif statut == 'rejete':
                messages.warning(request, "L'avis a été rejeté.")
            
            return redirect('avis:tableau_avis_gestionnaire')
    else:
        form = ModerationAvisForm(instance=avis, moderateur=request.user)
    
    context = {
        'form': form,
        'avis': avis,
        'title': 'Modération d\'avis'
    }
    
    return render(request, 'avis/moderer_avis.html', context)


# ============================================================================
# VUES AJAX - INTERACTIONS DYNAMIQUES
# ============================================================================

@require_POST
@login_required
@csrf_protect
def like_avis(request, avis_id):
    """Liker/unliker un avis en AJAX"""
    avis = get_object_or_404(Avis, id=avis_id, statut_moderation='approuve')
    
    like_obj, created = LikeAvis.objects.get_or_create(
        avis=avis,
        user=request.user
    )
    
    if not created:
        # Unlike
        like_obj.delete()
        liked = False
        avis.nombre_likes = max(0, avis.nombre_likes - 1)
    else:
        # Like
        liked = True
        avis.nombre_likes += 1
    
    avis.save()
    
    return JsonResponse({
        'liked': liked,
        'nombre_likes': avis.nombre_likes
    })


@require_POST
@login_required
@csrf_protect
def signaler_avis(request, avis_id):
    """Signaler un avis en AJAX"""
    avis = get_object_or_404(Avis, id=avis_id, statut_moderation='approuve')
    
    # Vérifier que l'utilisateur n'a pas déjà signalé
    if SignalementAvis.objects.filter(avis=avis, user=request.user).exists():
        return JsonResponse({
            'success': False,
            'message': 'Vous avez déjà signalé cet avis.'
        })
    
    form = SignalementAvisForm(request.POST, user=request.user, avis=avis)
    if form.is_valid():
        form.save()
        avis.nombre_signalements += 1
        avis.save()
        
        # Auto-masquer si trop de signalements
        if avis.nombre_signalements >= 5:
            avis.statut_moderation = 'signale'
            avis.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Avis signalé avec succès. Merci pour votre vigilance.'
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Erreur lors du signalement.'
        })


@login_required
def widget_avis_maison(request, maison_id):
    """Widget des avis pour une maison (pour inclusion dans d'autres pages)"""
    maison = get_object_or_404(Maison, id=maison_id)
    
    avis_recents = maison.avis.filter(
        statut_moderation='approuve'
    ).order_by('-date_creation')[:3]
    
    stats = {
        'note_moyenne': maison.note_moyenne,
        'nombre_avis': maison.nombre_avis,
        'pourcentage_recommandation': maison.get_pourcentage_recommandation()
    }
    
    context = {
        'maison': maison,
        'avis_recents': avis_recents,
        'stats': stats
    }
    
    return render(request, 'avis/widgets/widget_avis_maison.html', context)


# ============================================================================
# VUES ADMIN - GESTION AVANCEE
# ============================================================================

@login_required
def statistiques_avis(request):
    """Statistiques globales des avis (super admin uniquement)"""
    if not request.user.is_super_admin():
        messages.error(request, "Accès non autorisé.")
        return redirect('home:index')
    
    from django.db.models import Count, Avg
    from datetime import datetime, timedelta
    
    # Statistiques générales
    stats_generales = {
        'total_avis': Avis.objects.count(),
        'avis_publies': Avis.objects.filter(statut_moderation='approuve').count(),
        'avis_en_attente': Avis.objects.filter(statut_moderation='en_attente').count(),
        'note_moyenne_globale': Avis.objects.filter(
            statut_moderation='approuve'
        ).aggregate(moyenne=Avg('note'))['moyenne'] or 0
    }
    
    # Évolution mensuelle
    derniers_mois = []
    for i in range(6):
        date_debut = datetime.now().replace(day=1) - timedelta(days=30*i)
        date_fin = (date_debut + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        count = Avis.objects.filter(
            date_creation__range=[date_debut, date_fin]
        ).count()
        
        derniers_mois.append({
            'mois': date_debut.strftime('%B %Y'),
            'count': count
        })
    
    # Top maisons par avis
    top_maisons = Maison.objects.annotate(
        nb_avis=Count('avis', filter=Q(avis__statut_moderation='approuve'))
    ).order_by('-nb_avis')[:10]
    
    context = {
        'stats_generales': stats_generales,
        'evolution_mensuelle': reversed(derniers_mois),
        'top_maisons': top_maisons,
        'title': 'Statistiques des avis'
    }
    
    return render(request, 'avis/statistiques_avis.html', context)