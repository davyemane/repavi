# apps/facturation/views.py - Facturation PDF selon cahier
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.template.loader import get_template
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from datetime import datetime
from .models import Facture
from .forms import FactureForm
from apps.reservations.models import Reservation

def is_gestionnaire(user):
    return user.is_authenticated and user.profil in ['gestionnaire', 'super_admin']

@login_required
@user_passes_test(is_gestionnaire)
def liste_factures(request):
    """Liste des factures générées"""
    factures = Facture.objects.select_related(
        'reservation__client',
        'reservation__appartement'
    ).order_by('-date_creation')
    
    context = {
        'factures': factures,
    }
    return render(request, 'facturation/liste.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def generer_facture(request):
    """
    Génération facture PDF selon cahier des charges
    Facture PDF avec logo RepAvi Lodges
    """
    # Réservations facturables (terminées sans facture)
    reservations_facturables = Reservation.objects.filter(
        statut='terminee'
    ).exclude(
        facture__isnull=False
    ).select_related('client', 'appartement')
    
    if request.method == 'POST':
        reservation_id = request.POST.get('reservation_id')
        if not reservation_id:
            messages.error(request, 'Veuillez sélectionner une réservation')
            return redirect('facturation:generer')
        
        reservation = get_object_or_404(Reservation, pk=reservation_id)
        
        # Créer la facture selon cahier
        facture = Facture.objects.create(
            reservation=reservation,
            frais_supplementaires=float(request.POST.get('frais_supplementaires', 0)),
            gestionnaire=request.user
        )
        
        # Générer le PDF selon cahier
        pdf_file = generer_pdf_facture(facture)
        facture.fichier_pdf.save(
            f'facture_{facture.numero_facture}.pdf',
            pdf_file,
            save=True
        )
        
        messages.success(request, f'Facture {facture.numero_facture} générée avec succès !')
        return redirect('facturation:apercu', pk=facture.pk)
    
    form = FactureForm()
    context = {
        'form': form,
        'reservations_facturables': reservations_facturables,
    }
    return render(request, 'facturation/generer.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def generer_facture_reservation(request, reservation_pk):
    """Générer facture directement depuis une réservation"""
    reservation = get_object_or_404(Reservation, pk=reservation_pk)
    
    # Vérifier si facture existe déjà
    if hasattr(reservation, 'facture'):
        messages.info(request, 'Une facture existe déjà pour cette réservation')
        return redirect('facturation:apercu', pk=reservation.facture.pk)
    
    # Créer facture selon cahier
    facture = Facture.objects.create(
        reservation=reservation,
        gestionnaire=request.user
    )
    
    # Générer PDF
    pdf_file = generer_pdf_facture(facture)
    facture.fichier_pdf.save(
        f'facture_{facture.numero_facture}.pdf',
        pdf_file,
        save=True
    )
    
    messages.success(request, f'Facture {facture.numero_facture} générée !')
    return redirect('facturation:apercu', pk=facture.pk)

@login_required
@user_passes_test(is_gestionnaire)
def telecharger_pdf(request, pk):
    """Télécharger le PDF de la facture"""
    facture = get_object_or_404(Facture, pk=pk)
    
    if not facture.fichier_pdf:
        # Régénérer si fichier manquant
        pdf_file = generer_pdf_facture(facture)
        facture.fichier_pdf.save(
            f'facture_{facture.numero_facture}.pdf',
            pdf_file,
            save=True
        )
    
    return FileResponse(
        facture.fichier_pdf,
        as_attachment=True,
        filename=f'Facture_{facture.numero_facture}.pdf'
    )

def generer_pdf_facture(facture):
    """
    Génération PDF selon cahier des charges
    Informations complètes : client, séjour, détail coûts, plan paiement
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # En-tête RepAvi Lodges selon cahier
    story.append(Paragraph(
        '<b>REPAVI LODGES</b><br/>Gestion de maisons meublées<br/>Douala, Cameroun',
        styles['Normal']
    ))
    story.append(Spacer(1, 20))
    
    # Numéro facture automatique selon cahier
    story.append(Paragraph(
        f'<b>FACTURE N° {facture.numero_facture}</b><br/>'
        f'Date d\'émission : {facture.date_emission.strftime("%d/%m/%Y")}',
        styles['Normal']
    ))
    story.append(Spacer(1, 30))
    
    # Informations client selon cahier
    client = facture.reservation.client
    story.append(Paragraph('<b>INFORMATIONS CLIENT :</b>', styles['Normal']))
    story.append(Paragraph(
        f'{client.prenom} {client.nom}<br/>'
        f'Téléphone : {client.telephone}<br/>'
        f'Email : {client.email}<br/>'
        f'Adresse : {client.adresse_residence}',
        styles['Normal']
    ))
    story.append(Spacer(1, 20))
    
    # Détail du séjour selon cahier
    reservation = facture.reservation
    story.append(Paragraph('<b>DÉTAIL DU SÉJOUR :</b>', styles['Normal']))
    story.append(Paragraph(
        f'Appartement : {reservation.appartement.numero} ({reservation.appartement.get_type_logement_display()})<br/>'
        f'Maison : {reservation.appartement.maison}<br/>'
        f'Dates : {reservation.date_arrivee.strftime("%d/%m/%Y")} → {reservation.date_depart.strftime("%d/%m/%Y")}<br/>'
        f'Nombre de nuits : {reservation.nombre_nuits}',
        styles['Normal']
    ))
    story.append(Spacer(1, 30))
    
    # Détail des coûts selon cahier
    data_table = [
        ['Description', 'Quantité', 'Prix Unitaire', 'Total'],
        [
            f'Séjour {reservation.appartement.numero}',
            f'{reservation.nombre_nuits} nuits',
            f'{reservation.appartement.prix_par_nuit:,.0f} FCFA',
            f'{reservation.prix_total:,.0f} FCFA'
        ]
    ]
    
    # Frais supplémentaires si applicable
    if facture.frais_supplementaires > 0:
        data_table.append([
            'Frais supplémentaires',
            '1',
            f'{facture.frais_supplementaires:,.0f} FCFA',
            f'{facture.frais_supplementaires:,.0f} FCFA'
        ])
    
    # Total selon cahier
    data_table.append([
        '', '', 'TOTAL À PAYER',
        f'{facture.montant_total:,.0f} FCFA'
    ])
    
    table = Table(data_table)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 30))
    
    # Plan de paiement si échéancé selon cahier
    from apps.paiements.models import EcheancierPaiement
    echeances = EcheancierPaiement.objects.filter(reservation=reservation)
    
    if echeances.exists():
        story.append(Paragraph('<b>PLAN DE PAIEMENT :</b>', styles['Normal']))
        for echeance in echeances:
            statut_text = "✅ Payé" if echeance.statut == 'paye' else "⏳ En attente"
            story.append(Paragraph(
                f'• {echeance.get_type_paiement_display()} : {echeance.montant_prevu:,.0f} FCFA '
                f'(Échéance : {echeance.date_echeance.strftime("%d/%m/%Y")}) - {statut_text}',
                styles['Normal']
            ))
    
    # Construire le PDF
    doc.build(story)
    buffer.seek(0)
    
    return buffer

#appercu de la facture
@login_required
@user_passes_test(is_gestionnaire)
def apercu_facture(request, pk):
    """Aperçu de la facture selon cahier"""
    facture = get_object_or_404(Facture, pk=pk)
    
    # Historique des séjours selon cahier
    reservations = Reservation.objects.filter(facture=facture).order_by('-date_arrivee')
    
    context = {
        'facture': facture,
        'reservations': reservations,
    }
    return render(request, 'facturation/apercu_facture.html', context)

@login_required
@user_passes_test(is_gestionnaire)
def regenerer_facture(request, pk):
    """Régénérer la facture selon cahier"""
    facture = get_object_or_404(Facture, pk=pk)
    buffer = generer_facture(facture)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="facture_{facture.id}.pdf"'
    return response
