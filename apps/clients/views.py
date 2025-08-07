# ==========================================
# apps/clients/views.py - Gestion clients simple
# ==========================================
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q

from apps.reservations.models import Reservation
from apps.users.views import is_gestionnaire
from .models import Client
from .forms import ClientForm

@login_required
@user_passes_test(is_gestionnaire)
def liste_clients(request):
    """Liste des clients avec recherche selon cahier"""
    clients = Client.objects.all()
    
    # Recherche par nom ou téléphone selon cahier
    recherche = request.GET.get('q')
    if recherche:
        clients = clients.filter(
            Q(nom__icontains=recherche) | 
            Q(prenom__icontains=recherche) |
            Q(telephone__icontains=recherche)
        )
    
    context = {
        'clients': clients,
        'recherche': recherche,
    }
    return render(request, 'clients/liste.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def detail_client(request, pk):
    """Fiche client avec historique des séjours selon cahier"""
    client = get_object_or_404(Client, pk=pk)
    
    # Historique des séjours selon cahier
    from apps.reservations.models import Reservation
    reservations = Reservation.objects.filter(client=client).order_by('-date_arrivee')
    
    context = {
        'client': client,
        'reservations': reservations,
        'nombre_sejours': client.get_nombre_sejours(),
    }
    return render(request, 'clients/detail.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def creer_client(request):
    """Créer nouvelle fiche client selon cahier"""
    if request.method == 'POST':
        form = ClientForm(request.POST, request.FILES)
        if form.is_valid():
            client = form.save()
            messages.success(request, f'Client {client.prenom} {client.nom} créé avec succès !')
            return redirect('clients:detail', pk=client.pk)
    else:
        form = ClientForm()
    
    return render(request, 'clients/formulaire.html', {
        'form': form,
        'titre': 'Nouveau Client',
        'action': 'Créer'
    })

#modifier_client
@login_required
@user_passes_test(is_gestionnaire)
def modifier_client(request, pk):
    """Modifier un client selon cahier"""
    client = get_object_or_404(Client, pk=pk)
    
    if request.method == 'POST':
        form = ClientForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            client = form.save(commit=False)
            client.gestionnaire = request.user
            client.save()
            
            messages.success(request, f'Client {client.prenom} {client.nom} modifié avec succès !')
            return redirect('clients:detail', pk=client.pk)
    else:
        form = ClientForm(instance=client)
    
    return render(request, 'clients/modifier_client.html', {
        'form': form,
        'client': client,
        'titre': f'Modifier {client.prenom} {client.nom}',
        'action': 'Modifier'
    })

@login_required
@user_passes_test(is_gestionnaire)
def historique_sejours(request, pk):
    """Historique des séjours selon cahier"""
    client = get_object_or_404(Client, pk=pk)
    
    # Historique des séjours selon cahier
    reservations = Reservation.objects.filter(client=client).order_by('-date_arrivee')
    
    context = {
        'client': client,
        'reservations': reservations,
    }
    return render(request, 'clients/historique_sejours.html', context)  

@login_required
@user_passes_test(is_gestionnaire)
def recherche_clients(request):
    """Recherche de clients selon cahier"""
    if request.method == 'POST':
        q = request.POST.get('q')
        clients = Client.objects.filter(
            Q(nom__icontains=q) | 
            Q(prenom__icontains=q) |
            Q(telephone__icontains=q)
        )
        
        context = {
            'clients': clients,
            'q': q,
        }
        return render(request, 'clients/recherche_clients.html', context)
    else:
        messages.error(request, 'Veuillez utiliser le formulaire de recherche.')
        return redirect('clients:liste')