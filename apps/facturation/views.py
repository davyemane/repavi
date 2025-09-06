# ==========================================
# apps/facturation/views.py
# ==========================================
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.template.loader import get_template
from django.conf import settings
from django.urls import reverse
from datetime import datetime, timedelta
import os
from io import BytesIO
from django.db.models import Sum

# Import pour PDF
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from apps.users.views import is_gestionnaire
from apps.reservations.models import Reservation
from .models import Facture, ParametresFacturation


@login_required
@user_passes_test(is_gestionnaire)
def liste_factures(request):
    """Liste des factures RepAvi"""
    factures = Facture.objects.select_related('client', 'reservation').all()
    
    # Filtres
    statut = request.GET.get('statut')
    if statut:
        factures = factures.filter(statut=statut)
    
    mois = request.GET.get('mois')
    if mois:
        try:
            annee, mois_num = mois.split('-')
            factures = factures.filter(
                date_emission__year=int(annee),
                date_emission__month=int(mois_num)
            )
        except ValueError:
            pass
    
    context = {
        'factures': factures,
        'statut_filtre': statut,
        'mois_filtre': mois,
        'statuts': Facture.STATUT_CHOICES,
    }
    return render(request, 'facturation/liste.html', context)


@login_required
@user_passes_test(is_gestionnaire)
def detail_facture(request, pk):
    """Détail d'une facture"""
    facture = get_object_or_404(Facture, pk=pk)
    
    context = {
        'facture': facture,
        'lignes': facture.get_lignes_facture(),
        'details_sejour': facture.get_details_sejour(),
        'parametres': ParametresFacturation.get_parametres(),
    }
    return render(request, 'facturation/detail.html', context)


@login_required
@user_passes_test(is_gestionnaire)
def generer_facture_reservation(request, reservation_pk):
    """Génère une facture pour une réservation"""
    reservation = get_object_or_404(Reservation, pk=reservation_pk)
    
    # Vérifier qu'il n'y a pas déjà une facture
    if hasattr(reservation, 'facture'):
        messages.warning(request, 'Une facture existe déjà pour cette réservation.')
        return redirect('facturation:detail', pk=reservation.facture.pk)
    
    if request.method == 'POST':
        # Récupérer les paramètres par défaut
        parametres = ParametresFacturation.get_parametres()
        
        # Créer la facture - CORRECTION: Assigner cree_par
        facture = Facture(
            reservation=reservation,
            client=reservation.client,
            date_echeance=datetime.now().date() + timedelta(days=parametres.delai_paiement_jours),
            frais_menage=float(request.POST.get('frais_menage', parametres.frais_menage_defaut)),
            frais_service=float(request.POST.get('frais_service', 0)),
            remise=float(request.POST.get('remise', 0)),
            notes=request.POST.get('notes', ''),
            cree_par=request.user,  # ← CORRECTION: Assigner l'utilisateur
        )
        facture.save()
        
        messages.success(request, f'Facture {facture.numero} générée avec succès !')
        return redirect('facturation:detail', pk=facture.pk)
    
    # Affichage du formulaire
    parametres = ParametresFacturation.get_parametres()
    context = {
        'reservation': reservation,
        'parametres': parametres,
    }
    return render(request, 'facturation/generer.html', context)


@login_required
@user_passes_test(is_gestionnaire)
def facture_pdf(request, pk):
    """Génère le PDF d'une facture - VERSION AMÉLIORÉE"""
    if not WEASYPRINT_AVAILABLE:
        messages.error(request, 'La génération PDF n\'est pas disponible. Veuillez installer WeasyPrint.')
        return redirect('facturation:detail', pk=pk)
    
    facture = get_object_or_404(Facture, pk=pk)
    
    # Contexte pour le template PDF
    context = {
        'facture': facture,
        'lignes': facture.get_lignes_facture(),
        'details_sejour': facture.get_details_sejour(),
        'parametres': ParametresFacturation.get_parametres(),
        'date_impression': datetime.now(),
        'user': request.user,
        'STATIC_URL': settings.STATIC_URL,  # ← AJOUT: Pour les images
    }
    
    # Rendu du template HTML
    template = get_template('facturation/facture_pdf.html')
    html_string = template.render(context)
    
    # Configuration des polices
    font_config = FontConfiguration()
    
    # CSS amélioré pour le PDF avec filigrane
    css_content = f"""
        @page {{
            size: A4;
            margin: 15mm 12mm;
        }}
        
        body {{
            font-family: 'DejaVu Sans', Arial, sans-serif;
            font-size: 11px;
            line-height: 1.4;
            color: #1f2937;
            position: relative;
        }}
        
        /* Filigrane en CSS (fallback si l'image ne charge pas) */
        body::before {{
            content: '';
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 400px;
            height: 400px;
            background-image: url('data:image/svg+xml;charset=utf-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y="50" font-size="20" fill="rgba(2,6,111,0.03)" text-anchor="middle">RepAvi</text></svg>');
            background-repeat: no-repeat;
            background-position: center;
            background-size: contain;
            z-index: -1;
            pointer-events: none;
        }}
        
        .container {{
            position: relative;
            z-index: 1;
            background: rgba(255, 255, 255, 0.98);
        }}
        
        /* Styles optimisés pour WeasyPrint */
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 20px 0;
            border-bottom: 3px solid #02066F;
            margin-bottom: 25px;
        }}
        
        .logo-section {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .company-info h1 {{
            font-size: 24px;
            font-weight: bold;
            color: #02066F;
            margin: 0;
        }}
        
        .facture-title {{
            background: #02066F;
            color: white;
            padding: 15px;
            text-align: center;
            margin-bottom: 20px;
        }}
        
        .facture-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        
        .facture-table th {{
            background: #02066F;
            color: white;
            padding: 10px;
            text-align: center;
            font-weight: bold;
        }}
        
        .facture-table td {{
            padding: 8px;
            border: 1px solid #e5e7eb;
            text-align: center;
        }}
        
        .totaux-table {{
            border: 2px solid #02066F;
            margin-left: auto;
            margin-top: 20px;
        }}
        
        .totaux-table td {{
            padding: 8px 15px;
            border-bottom: 1px solid #e5e7eb;
        }}
        
        .total-final td {{
            background: #02066F;
            color: white;
            font-weight: bold;
        }}
    """
    
    # Génération du PDF
    try:
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        css = CSS(string=css_content, font_config=font_config)
        pdf_file = html.write_pdf(stylesheets=[css], font_config=font_config)
        
        # Réponse HTTP avec le PDF
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Facture_{facture.numero}.pdf"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'Erreur lors de la génération du PDF : {str(e)}')
        return redirect('facturation:detail', pk=pk)


@login_required
@user_passes_test(is_gestionnaire)
def facture_preview(request, pk):
    """Aperçu HTML de la facture (pour debug) - VERSION AMÉLIORÉE"""
    facture = get_object_or_404(Facture, pk=pk)
    
    context = {
        'facture': facture,
        'lignes': facture.get_lignes_facture(),
        'details_sejour': facture.get_details_sejour(),
        'parametres': ParametresFacturation.get_parametres(),
        'date_impression': datetime.now(),
        'user': request.user,
        'STATIC_URL': settings.STATIC_URL,  # ← AJOUT: Pour les images
        'preview': True,  # Pour afficher des styles différents
    }
    
    return render(request, 'facturation/facture_pdf.html', context)




@login_required
@user_passes_test(is_gestionnaire)
def modifier_facture(request, pk):
    """Modifier une facture"""
    facture = get_object_or_404(Facture, pk=pk)
    
    if facture.statut == 'payee':
        messages.error(request, 'Impossible de modifier une facture payée.')
        return redirect('facturation:detail', pk=pk)
    
    if request.method == 'POST':
        # Mise à jour des champs
        facture.frais_menage = float(request.POST.get('frais_menage', 0))
        facture.frais_service = float(request.POST.get('frais_service', 0))
        facture.remise = float(request.POST.get('remise', 0))
        facture.notes = request.POST.get('notes', '')
        facture.conditions_paiement = request.POST.get('conditions_paiement', facture.conditions_paiement)
        
        # Nouveau statut
        nouveau_statut = request.POST.get('statut')
        if nouveau_statut in dict(Facture.STATUT_CHOICES):
            facture.statut = nouveau_statut
        
        facture.save()
        
        messages.success(request, 'Facture modifiée avec succès !')
        return redirect('facturation:detail', pk=pk)
    
    context = {
        'facture': facture,
        'statuts': Facture.STATUT_CHOICES,
    }
    return render(request, 'facturation/modifier.html', context)


@login_required
@user_passes_test(is_gestionnaire)
def marquer_payee(request, pk):
    """Marquer une facture comme payée"""
    facture = get_object_or_404(Facture, pk=pk)
    
    if request.method == 'POST':
        facture.statut = 'payee'
        facture.save()
        
        messages.success(request, f'Facture {facture.numero} marquée comme payée !')
    
    return redirect('facturation:detail', pk=pk)


@login_required
@user_passes_test(is_gestionnaire)
def annuler_facture(request, pk):
    """Annuler une facture"""
    facture = get_object_or_404(Facture, pk=pk)
    
    if facture.statut == 'payee':
        messages.error(request, 'Impossible d\'annuler une facture payée.')
        return redirect('facturation:detail', pk=pk)
    
    if request.method == 'POST':
        facture.statut = 'annulee'
        facture.save()
        
        messages.success(request, f'Facture {facture.numero} annulée !')
    
    return redirect('facturation:detail', pk=pk)


@login_required
@user_passes_test(is_gestionnaire)
def parametres_facturation(request):
    """Gestion des paramètres de facturation"""
    parametres = ParametresFacturation.get_parametres()
    
    if request.method == 'POST':
        # Mise à jour des paramètres
        parametres.nom_entreprise = request.POST.get('nom_entreprise')
        parametres.adresse = request.POST.get('adresse')
        parametres.telephone = request.POST.get('telephone')
        parametres.email = request.POST.get('email')
        parametres.site_web = request.POST.get('site_web', '')
        parametres.numero_contribuable = request.POST.get('numero_contribuable', '')
        parametres.numero_rccm = request.POST.get('numero_rccm', '')
        parametres.taux_tva_defaut = float(request.POST.get('taux_tva_defaut'))
        parametres.frais_menage_defaut = float(request.POST.get('frais_menage_defaut'))
        parametres.delai_paiement_jours = int(request.POST.get('delai_paiement_jours'))
        parametres.conditions_generales = request.POST.get('conditions_generales')
        parametres.mentions_legales = request.POST.get('mentions_legales')
        
        parametres.save()
        
        messages.success(request, 'Paramètres de facturation mis à jour !')
        return redirect('facturation:parametres')
    
    context = {
        'parametres': parametres,
    }
    return render(request, 'facturation/parametres.html', context)


@login_required
@user_passes_test(is_gestionnaire)
def dashboard_facturation(request):
    """Dashboard de facturation avec statistiques - CORRIGÉ"""
    maintenant = datetime.now()
    
    # Statistiques du mois en cours
    factures_mois = Facture.objects.filter(
        date_emission__year=maintenant.year,
        date_emission__month=maintenant.month
    )
    
    # CORRECTION : Variables attendues par le template
    montant_total_result = factures_mois.aggregate(total=Sum('montant_ttc'))
    montant_total_mois = montant_total_result.get('total') or 0
    
    stats = {
        'total_factures_mois': factures_mois.count(),
        'montant_total_mois': montant_total_mois,
        'factures_payees': factures_mois.filter(statut='payee').count(),
        'factures_en_attente': factures_mois.filter(statut='emise').count(),
        'taux_paiement': 0,
    }
    
    # Calcul du taux de paiement
    if stats['total_factures_mois'] > 0:
        stats['taux_paiement'] = round(
            (stats['factures_payees'] / stats['total_factures_mois']) * 100, 1
        )
    
    # Dernières factures
    dernieres_factures = Facture.objects.select_related(
        'client', 'reservation'
    ).order_by('-date_emission')[:10]
    
    # Factures en retard
    factures_retard = Facture.objects.filter(
        statut='emise',
        date_echeance__lt=maintenant.date()
    ).select_related('client')[:5]
    
    context = {
        'stats': stats,
        'dernieres_factures': dernieres_factures,
        'factures_retard': factures_retard,
        'mois_actuel': maintenant,
    }
    
    return render(request, 'facturation/dashboard.html', context)