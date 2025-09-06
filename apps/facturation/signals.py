# ==========================================
# apps/facturation/signals.py - FACTURATION PAR TRANCHE
# ==========================================
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from apps.reservations.models import Reservation
from apps.paiements.models import EcheancierPaiement
from .models import Facture, ParametresFacturation

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=EcheancierPaiement)
def creer_facture_apres_chaque_paiement(sender, instance, created, **kwargs):
    """
    Crée une facture à chaque paiement effectué (acompte OU solde)
    """
    # Ne traiter que les paiements qui viennent d'être marqués comme payés
    if instance.statut != 'paye':
        return
    
    try:
        # Vérifier si une facture existe déjà pour ce paiement spécifique
        try:
            facture_existante = Facture.objects.get(echeance_paiement=instance)
            logger.info(f"Facture {facture_existante.numero} existe déjà pour le paiement {instance.pk}")
            return
        except Facture.DoesNotExist:
            # Pas de facture pour ce paiement, continuer
            pass
        
        # Récupérer les paramètres
        parametres = ParametresFacturation.get_parametres()
        
        # Créer la facture pour ce paiement spécifique
        facture = Facture.objects.create(
            echeance_paiement=instance,
            date_echeance=datetime.now().date() + timedelta(days=parametres.delai_paiement_jours),
            notes=f"Facture générée automatiquement pour {instance.get_type_paiement_display().lower()} le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            statut='payee',  # Directement payée puisque paiement effectué
            cree_par=None  # Création automatique
        )
        
        # Calculer le contexte du paiement (soldes avant/après)
        facture.calculer_contexte_paiement()
        facture.save()
        
        logger.info(f"✅ Facture {facture.numero} créée pour {instance.get_type_paiement_display()} de {instance.montant_paye} FCFA")
        
        # Notifier les gestionnaires
        notifier_facture_generee(facture)
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de facture pour le paiement {instance.pk}: {e}")
        import traceback
        traceback.print_exc()


def notifier_facture_generee(facture):
    """
    Notifie les gestionnaires qu'une facture a été générée
    """
    try:
        gestionnaires = User.objects.filter(
            profil__in=['gestionnaire', 'super_admin'],
            is_active=True,
            email__isnull=False
        ).exclude(email='')
        
        if gestionnaires.exists():
            # Déterminer si c'est le paiement final
            est_final = facture.est_paiement_final
            type_paiement = facture.get_type_facture_display()
            
            sujet = f"RepAvi Lodges - Facture {type_paiement} {facture.numero}"
            
            # Message détaillé
            message = f"""
Nouvelle facture générée automatiquement :

Facture : {facture.numero}
Type : {type_paiement}
Client : {facture.client.nom} {facture.client.prenom}
Réservation : #{facture.reservation.pk}
Appartement : {facture.reservation.appartement.numero}

PAIEMENT :
• Montant payé : {facture.montant_paiement} FCFA
• Date paiement : {facture.echeance_paiement.date_paiement}
• Mode : {facture.echeance_paiement.get_mode_paiement_display() or 'Non spécifié'}

SITUATION :
• Solde avant : {facture.solde_avant_paiement} FCFA
• Solde après : {facture.solde_apres_paiement} FCFA
{'• 🎉 RÉSERVATION ENTIÈREMENT PAYÉE !' if est_final else '• ⏳ Solde restant à payer'}

Période : du {facture.reservation.date_arrivee} au {facture.reservation.date_depart}

📄 Télécharger PDF : /facturation/{facture.pk}/pdf/

RepAvi Lodges
            """
            
            emails_gestionnaires = [g.email for g in gestionnaires]
            
            send_mail(
                subject=sujet,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@repavilodges.com'),
                recipient_list=emails_gestionnaires,
                fail_silently=True
            )
            
            logger.info(f"📧 Notification envoyée pour facture {type_paiement} {facture.numero}")
        
    except Exception as e:
        logger.error(f"❌ Erreur notification facture {facture.numero}: {e}")


# Fonction utilitaire pour créer manuellement une facture
def creer_facture_manuelle_paiement(echeance_paiement, user=None, **kwargs):
    """
    Crée manuellement une facture pour un paiement spécifique
    """
    try:
        # Vérifier qu'il n'y a pas déjà une facture pour ce paiement
        try:
            facture_existante = Facture.objects.get(echeance_paiement=echeance_paiement)
            raise ValueError(f"Une facture existe déjà pour ce paiement: {facture_existante.numero}")
        except Facture.DoesNotExist:
            pass
        
        # Vérifier que le paiement est payé
        if echeance_paiement.statut != 'paye':
            raise ValueError("Impossible de créer une facture pour un paiement non effectué")
        
        parametres = ParametresFacturation.get_parametres()
        
        # Valeurs par défaut
        defaults = {
            'date_echeance': datetime.now().date() + timedelta(days=parametres.delai_paiement_jours),
            'notes': f"Facture créée manuellement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            'statut': 'payee',
        }
        
        # Fusionner avec les kwargs fournis
        defaults.update(kwargs)
        
        facture = Facture.objects.create(
            echeance_paiement=echeance_paiement,
            cree_par=user,
            **defaults
        )
        
        # Calculer le contexte
        facture.calculer_contexte_paiement()
        facture.save()
        
        logger.info(f"📋 Facture {facture.numero} créée manuellement pour paiement {echeance_paiement.pk}")
        return facture
        
    except Exception as e:
        logger.error(f"❌ Erreur création facture manuelle pour paiement {echeance_paiement.pk}: {e}")
        raise


# Fonction de diagnostic
def diagnostic_factures_manquantes():
    """
    Trouve les paiements sans facture
    """
    paiements_sans_facture = EcheancierPaiement.objects.filter(
        statut='paye',
        facture__isnull=True
    )
    
    print(f"🔍 {paiements_sans_facture.count()} paiements sans facture trouvés")
    
    for paiement in paiements_sans_facture:
        print(f"  - Paiement #{paiement.pk}: {paiement.get_type_paiement_display()} de {paiement.montant_paye} FCFA (Réservation #{paiement.reservation.pk})")
    
    return paiements_sans_facture


def creer_factures_manquantes():
    """
    Crée toutes les factures manquantes pour les paiements effectués
    """
    paiements_sans_facture = diagnostic_factures_manquantes()
    
    factures_creees = 0
    erreurs = 0
    
    for paiement in paiements_sans_facture:
        try:
            facture = creer_facture_manuelle_paiement(
                echeance_paiement=paiement,
                notes=f"Facture créée en lot pour paiement du {paiement.date_paiement}"
            )
            print(f"✅ Facture {facture.numero} créée pour paiement #{paiement.pk}")
            factures_creees += 1
            
        except Exception as e:
            print(f"❌ Erreur paiement #{paiement.pk}: {e}")
            erreurs += 1
    
    print(f"\n📊 RÉSULTAT: {factures_creees} factures créées, {erreurs} erreurs")
    return factures_creees, erreurs