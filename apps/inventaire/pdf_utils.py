# apps/inventaire/pdf_utils.py
from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import tempfile
import os
from datetime import datetime

from apps.appartements.models import Appartement
from apps.users.views import is_gestionnaire
from .models import EquipementAppartement

@login_required
@user_passes_test(is_gestionnaire)
def generer_pdf_inventaire(request, appartement_pk):
    """Génère un PDF du rapport d'inventaire selon cahier"""
    appartement = get_object_or_404(Appartement, pk=appartement_pk)
    
    equipements = appartement.inventaire_equipements.all()
    valeur_totale = equipements.aggregate(total=Sum('prix_achat'))['total'] or 0
    
    # Statistiques par état
    valeurs_par_etat = {}
    for etat_code, etat_nom in EquipementAppartement.ETAT_CHOICES:
        equipements_etat = equipements.filter(etat=etat_code)
        valeurs_par_etat[etat_code] = {
            'nom': etat_nom,
            'count': equipements_etat.count(),
            'valeur': equipements_etat.aggregate(total=Sum('prix_achat'))['total'] or 0
        }
    
    # Calculs pour indicateurs
    total_count = equipements.count()
    bon_count = valeurs_par_etat['bon']['count']
    pourcentage_bon = (bon_count / total_count * 100) if total_count > 0 else 0
    
    context = {
        'appartement': appartement,
        'equipements': equipements,
        'valeur_totale': valeur_totale,
        'valeurs_par_etat': valeurs_par_etat,
        'pourcentage_bon': pourcentage_bon,
        'date_generation': datetime.now(),
        'utilisateur': request.user,
    }
    
    # Rendu du template
    template = get_template('inventaire/pdf_rapport.html')
    html_string = template.render(context)
    
    # Configuration des fonts
    font_config = FontConfiguration()
    
    # CSS pour le PDF
    css_string = """
    @page {
        size: A4;
        margin: 2cm;
        @top-center {
            content: "RepAvi Lodges - Rapport d'Inventaire";
            font-size: 10pt;
            color: #666;
        }
        @bottom-center {
            content: "Page " counter(page) " sur " counter(pages);
            font-size: 10pt;
            color: #666;
        }
    }
    
    body {
        font-family: 'DejaVu Sans', sans-serif;
        font-size: 11pt;
        line-height: 1.4;
        color: #333;
    }
    
    .header {
        text-align: center;
        border-bottom: 2px solid #02066F;
        padding-bottom: 20px;
        margin-bottom: 30px;
    }
    
    .logo {
        font-size: 24pt;
        font-weight: bold;
        color: #02066F;
        margin-bottom: 10px;
    }
    
    .rapport-title {
        font-size: 18pt;
        font-weight: bold;
        margin-bottom: 5px;
    }
    
    .stats-grid {
        display: table;
        width: 100%;
        margin-bottom: 30px;
    }
    
    .stats-row {
        display: table-row;
    }
    
    .stats-cell {
        display: table-cell;
        width: 25%;
        padding: 15px;
        text-align: center;
        border: 1px solid #ddd;
    }
    
    .stats-number {
        font-size: 18pt;
        font-weight: bold;
        color: #02066F;
    }
    
    .equipement-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 30px;
    }
    
    .equipement-table th,
    .equipement-table td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    
    .equipement-table th {
        background-color: #f8f9fa;
        font-weight: bold;
        color: #02066F;
    }
    
    .etat-bon { color: #10b981; font-weight: bold; }
    .etat-usage { color: #3b82f6; font-weight: bold; }
    .etat-defectueux { color: #f59e0b; font-weight: bold; }
    .etat-hors-service { color: #ef4444; font-weight: bold; }
    
    .footer-info {
        margin-top: 30px;
        padding-top: 20px;
        border-top: 1px solid #ddd;
        font-size: 10pt;
        color: #666;
    }
    
    .break-inside-avoid {
        break-inside: avoid;
    }
    """
    
    # Génération du PDF
    html = HTML(string=html_string)
    css = CSS(string=css_string, font_config=font_config)
    
    # Nom du fichier
    filename = f"inventaire_{appartement.numero}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    html.write_pdf(response, stylesheets=[css], font_config=font_config)
    
    return response

@login_required
@user_passes_test(is_gestionnaire)
def generer_pdf_general(request):
    """Génère un PDF du rapport général d'inventaire"""
    appartements = Appartement.objects.all()
    
    # Statistiques globales
    total_equipements = EquipementAppartement.objects.count()
    valeur_totale = EquipementAppartement.objects.aggregate(total=Sum('prix_achat'))['total'] or 0
    valeur_moyenne = (valeur_totale / total_equipements) if total_equipements > 0 else 0
    
    # Données par appartement
    appartements_data = []
    for appartement in appartements:
        equipements = appartement.inventaire_equipements.all()
        nb_equipements = equipements.count()
        valeur_appt = equipements.aggregate(total=Sum('prix_achat'))['total'] or 0
        valeur_moyenne_appt = (valeur_appt / nb_equipements) if nb_equipements > 0 else 0
        
        appartements_data.append({
            'appartement': appartement,
            'nb_equipements': nb_equipements,
            'valeur_totale': valeur_appt,
            'valeur_moyenne': valeur_moyenne_appt,
            'equipements': equipements,
        })
    
    context = {
        'appartements_data': appartements_data,
        'total_equipements': total_equipements,
        'valeur_totale': valeur_totale,
        'valeur_moyenne': valeur_moyenne,
        'date_generation': datetime.now(),
        'utilisateur': request.user,
    }
    
    template = get_template('inventaire/pdf_general.html')
    html_string = template.render(context)
    
    font_config = FontConfiguration()
    css = CSS(string="""
    @page { size: A4; margin: 2cm; }
    body { font-family: 'DejaVu Sans', sans-serif; font-size: 11pt; }
    .header { text-align: center; border-bottom: 2px solid #02066F; padding-bottom: 20px; margin-bottom: 30px; }
    .logo { font-size: 24pt; font-weight: bold; color: #02066F; }
    .rapport-title { font-size: 18pt; font-weight: bold; margin-bottom: 5px; }
    .stats-grid { display: table; width: 100%; margin-bottom: 30px; }
    .stats-row { display: table-row; }
    .stats-cell { display: table-cell; width: 25%; padding: 15px; text-align: center; border: 1px solid #ddd; }
    .stats-number { font-size: 18pt; font-weight: bold; color: #02066F; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background-color: #f8f9fa; color: #02066F; font-weight: bold; }
    .etat-bon { color: #10b981; font-weight: bold; }
    .etat-usage { color: #3b82f6; font-weight: bold; }
    .etat-defectueux { color: #f59e0b; font-weight: bold; }
    .etat-hors-service { color: #ef4444; font-weight: bold; }
    .break-inside-avoid { break-inside: avoid; }
    .footer-info { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 10pt; color: #666; }
    """, font_config=font_config)
    
    html = HTML(string=html_string)
    filename = f"inventaire_general_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    html.write_pdf(response, stylesheets=[css], font_config=font_config)
    
    return response