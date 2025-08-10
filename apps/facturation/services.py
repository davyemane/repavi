# ==========================================
# apps/facturation/services.py - Service facturation
# ==========================================
from decimal import Decimal
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.core.files.base import ContentFile
from .models import Facture

class FacturationService:
    """Service pour gestion facturation selon cahier"""
    
    @staticmethod
    def creer_facture(reservation, frais_supplementaires=0, gestionnaire=None):
        """Créer facture pour une réservation"""
        facture = Facture.objects.create(
            reservation=reservation,
            frais_supplementaires=Decimal(str(frais_supplementaires)),
            gestionnaire=gestionnaire
        )
        
        # Générer PDF
        pdf_buffer = FacturationService.generer_pdf(facture)
        facture.fichier_pdf.save(
            f'facture_{facture.numero_facture}.pdf',
            ContentFile(pdf_buffer.getvalue()),
            save=True
        )
        
        # Notification
        if gestionnaire:
            from apps.notifications.models import NotificationService
            NotificationService.notify_facture_created(facture, gestionnaire)
        
        return facture
    
    @staticmethod
    def generer_pdf(facture):
        """Générer PDF selon cahier"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # En-tête RepAvi
        story.append(Paragraph(
            '<b>REPAVI LODGES</b><br/>Gestion de maisons meublées<br/>Douala, Cameroun',
            styles['Heading1']
        ))
        story.append(Spacer(1, 20))
        
        # Facture info
        story.append(Paragraph(
            f'<b>FACTURE N° {facture.numero_facture}</b><br/>'
            f'Date : {facture.date_emission.strftime("%d/%m/%Y")}',
            styles['Heading2']
        ))
        story.append(Spacer(1, 30))
        
        # Client
        client = facture.reservation.client
        story.append(Paragraph('<b>CLIENT :</b>', styles['Normal']))
        story.append(Paragraph(
            f'{client.prenom} {client.nom}<br/>'
            f'Tél: {client.telephone}<br/>'
            f'Email: {client.email or "Non renseigné"}',
            styles['Normal']
        ))
        story.append(Spacer(1, 20))
        
        # Séjour
        reservation = facture.reservation
        story.append(Paragraph('<b>SÉJOUR :</b>', styles['Normal']))
        story.append(Paragraph(
            f'Appartement: {reservation.appartement.numero}<br/>'
            f'Du {reservation.date_arrivee.strftime("%d/%m/%Y")} '
            f'au {reservation.date_depart.strftime("%d/%m/%Y")}<br/>'
            f'Durée: {reservation.nombre_nuits} nuit(s)',
            styles['Normal']
        ))
        story.append(Spacer(1, 30))
        
        # Tableau détail
        data = [
            ['Description', 'Quantité', 'Prix unitaire', 'Total'],
            [
                f'Séjour {reservation.appartement.numero}',
                f'{reservation.nombre_nuits} nuits',
                f'{reservation.appartement.prix_par_nuit:,.0f} FCFA',
                f'{facture.montant_sejour:,.0f} FCFA'
            ]
        ]
        
        if facture.frais_supplementaires > 0:
            data.append([
                'Frais supplémentaires',
                '1',
                f'{facture.frais_supplementaires:,.0f} FCFA',
                f'{facture.frais_supplementaires:,.0f} FCFA'
            ])
        
        data.append([
            '', '', '<b>TOTAL</b>',
            f'<b>{facture.montant_total:,.0f} FCFA</b>'
        ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.beige),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 30))
        
        # Plan paiement
        story.append(FacturationService._generer_plan_paiement(reservation, styles))
        
        # Footer
        story.append(Spacer(1, 50))
        story.append(Paragraph(
            'Merci de votre confiance !<br/>'
            'RepAvi Lodges - Votre confort, notre priorité',
            styles['Normal']
        ))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def _generer_plan_paiement(reservation, styles):
        """Plan de paiement dans PDF"""
        from apps.paiements.models import EcheancierPaiement
        
        echeances = EcheancierPaiement.objects.filter(reservation=reservation)
        if not echeances.exists():
            return Paragraph('')
        
        content = '<b>PLAN DE PAIEMENT :</b><br/>'
        for echeance in echeances:
            statut = "✅ Payé" if echeance.statut == 'paye' else "⏳ En attente"
            content += f'• {echeance.get_type_paiement_display()}: {echeance.montant_prevu:,.0f} FCFA - {statut}<br/>'
        
        return Paragraph(content, styles['Normal'])
    
    @staticmethod
    def get_reservations_facturables():
        """Réservations pouvant être facturées"""
        from apps.reservations.models import Reservation
        return Reservation.objects.filter(
            statut='terminee',
            facture__isnull=True
        ).select_related('client', 'appartement')
    
    @staticmethod
    def regenerer_pdf(facture):
        """Régénérer PDF existant"""
        pdf_buffer = FacturationService.generer_pdf(facture)
        facture.fichier_pdf.save(
            f'facture_{facture.numero_facture}.pdf',
            ContentFile(pdf_buffer.getvalue()),
            save=True
        )
        return facture