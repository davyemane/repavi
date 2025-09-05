# ==========================================
# apps/facturation/signals.py
# ==========================================
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import datetime, timedelta
import logging

from apps.reservations.models import Reservation
from .models import Facture, ParametresFacturation

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=Reservation)
def generer_facture_automatique(sender, instance, created, **kwargs):
    """
    Génère automatiquement une facture quand une réservation est confirmée
    """
    # Vérifier si la réservation est confirmée et n'a pas déjà de facture
    if (instance.statut == 'confirmee' and 
        not hasattr(instance, 'facture') and 
        not created):  # Pas lors de la création, seulement lors de la modification
        
        try:
            # Récupérer les paramètres par défaut
            parametres = ParametresFacturation.get_parametres()
            
            # Créer la facture automatiquement
            facture = Facture.objects.create(
                reservation=instance,
                client=instance.client,
                date_echeance=datetime.now().date() + timedelta(days=parametres.delai_paiement_jours),
                frais_menage=parametres.frais_menage_defaut,
                frais_service=0,
                remise=0,
                notes=f"Facture générée automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
                cree_par=None  # Création automatique
            )
            
            logger.info(f"Facture {facture.numero} générée automatiquement pour la réservation {instance.pk}")
            
            # Envoyer une notification aux gestionnaires
            notifier_facture_generee(facture)
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération automatique de facture pour la réservation {instance.pk}: {e}")


@receiver(pre_save, sender=Facture)
def calculer_montants_facture(sender, instance, **kwargs):
    """
    Calcule automatiquement les montants avant sauvegarde
    """
    if instance.reservation:
        # Recalculer les montants
        instance.calculer_montants()


@receiver(post_save, sender=Facture)
def notifier_creation_facture(sender, instance, created, **kwargs):
    """
    Notifie la création ou modification d'une facture
    """
    if created:
        # Nouvelle facture créée
        logger.info(f"Nouvelle facture créée: {instance.numero} pour {instance.client.nom}")
        
        # Optionnel: Envoyer par email
        if getattr(settings, 'FACTURATION_EMAIL_ENABLED', False):
            envoyer_facture_par_email(instance)
    
    else:
        # Facture modifiée
        if hasattr(instance, '_state') and instance._state.db:
            # Récupérer l'ancienne instance pour comparer
            try:
                ancienne_facture = Facture.objects.get(pk=instance.pk)
                if ancienne_facture.statut != instance.statut:
                    # Le statut a changé
                    logger.info(f"Statut de la facture {instance.numero} changé: {ancienne_facture.statut} → {instance.statut}")
                    
                    # Actions selon le nouveau statut
                    if instance.statut == 'payee':
                        notifier_facture_payee(instance)
                    elif instance.statut == 'annulee':
                        notifier_facture_annulee(instance)
                        
            except Facture.DoesNotExist:
                pass


def notifier_facture_generee(facture):
    """
    Notifie les gestionnaires qu'une facture a été générée
    """
    try:
        # Récupérer tous les gestionnaires actifs
        gestionnaires = User.objects.filter(
            profil__in=['gestionnaire', 'super_admin'],
            is_active=True,
            email__isnull=False
        ).exclude(email='')
        
        if not gestionnaires.exists():
            return
        
        # Préparer le message
        sujet = f"RepAvi - Nouvelle facture générée: {facture.numero}"
        
        # Template HTML
        contexte = {
            'facture': facture,
            'client': facture.client,
            'reservation': facture.reservation,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }
        
        message_html = render_to_string('facturation/emails/facture_generee.html', contexte)
        message_text = strip_tags(message_html)
        
        # Envoyer à tous les gestionnaires
        emails_gestionnaires = [g.email for g in gestionnaires]
        
        send_mail(
            subject=sujet,
            message=message_text,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@repavilodges.com'),
            recipient_list=emails_gestionnaires,
            html_message=message_html,
            fail_silently=True
        )
        
        logger.info(f"Notification envoyée aux gestionnaires pour la facture {facture.numero}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de notification pour la facture {facture.numero}: {e}")


def envoyer_facture_par_email(facture):
    """
    Envoie la facture par email au client
    """
    try:
        if not facture.client.email:
            logger.warning(f"Pas d'email pour le client {facture.client.nom} (facture {facture.numero})")
            return
        
        # Préparer le message pour le client
        sujet = f"RepAvi Lodges - Votre facture {facture.numero}"
        
        contexte = {
            'facture': facture,
            'client': facture.client,
            'reservation': facture.reservation,
            'parametres': ParametresFacturation.get_parametres(),
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }
        
        message_html = render_to_string('facturation/emails/facture_client.html', contexte)
        message_text = strip_tags(message_html)
        
        # TODO: Attacher le PDF de la facture
        # Il faudrait générer le PDF et l'attacher à l'email
        
        send_mail(
            subject=sujet,
            message=message_text,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@repavilodges.com'),
            recipient_list=[facture.client.email],
            html_message=message_html,
            fail_silently=True
        )
        
        logger.info(f"Facture {facture.numero} envoyée par email à {facture.client.email}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de la facture {facture.numero} par email: {e}")


def notifier_facture_payee(facture):
    """
    Notifie qu'une facture a été payée
    """
    try:
        # Marquer la réservation comme payée si nécessaire
        if hasattr(facture.reservation, 'statut_paiement'):
            facture.reservation.statut_paiement = 'paye'
            facture.reservation.save()
        
        logger.info(f"Facture {facture.numero} marquée comme payée")
        
        # Optionnel: Envoyer un reçu au client
        if getattr(settings, 'FACTURATION_EMAIL_ENABLED', False):
            envoyer_recu_paiement(facture)
            
    except Exception as e:
        logger.error(f"Erreur lors du traitement du paiement de la facture {facture.numero}: {e}")


def notifier_facture_annulee(facture):
    """
    Notifie qu'une facture a été annulée
    """
    try:
        logger.info(f"Facture {facture.numero} annulée")
        
        # Optionnel: Notifier le client de l'annulation
        if getattr(settings, 'FACTURATION_EMAIL_ENABLED', False) and facture.client.email:
            sujet = f"RepAvi Lodges - Annulation facture {facture.numero}"
            message = f"""
            Bonjour {facture.client.prenom} {facture.client.nom},
            
            Nous vous informons que la facture {facture.numero} a été annulée.
            
            Si vous avez des questions, n'hésitez pas à nous contacter.
            
            Cordialement,
            L'équipe RepAvi Lodges
            """
            
            send_mail(
                subject=sujet,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@repavilodges.com'),
                recipient_list=[facture.client.email],
                fail_silently=True
            )
            
    except Exception as e:
        logger.error(f"Erreur lors de la notification d'annulation de la facture {facture.numero}: {e}")


def envoyer_recu_paiement(facture):
    """
    Envoie un reçu de paiement au client
    """
    try:
        if not facture.client.email:
            return
        
        sujet = f"RepAvi Lodges - Reçu de paiement {facture.numero}"
        
        contexte = {
            'facture': facture,
            'client': facture.client,
            'parametres': ParametresFacturation.get_parametres(),
            'date_paiement': datetime.now(),
        }
        
        message_html = render_to_string('facturation/emails/recu_paiement.html', contexte)
        message_text = strip_tags(message_html)
        
        send_mail(
            subject=sujet,
            message=message_text,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@repavilodges.com'),
            recipient_list=[facture.client.email],
            html_message=message_html,
            fail_silently=True
        )
        
        logger.info(f"Reçu de paiement envoyé pour la facture {facture.numero}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du reçu pour la facture {facture.numero}: {e}")


# Signal pour nettoyer les factures brouillons anciennes
@receiver(post_save, sender=User)
def nettoyer_factures_brouillons(sender, instance, **kwargs):
    """
    Nettoie périodiquement les factures brouillons anciennes
    (Se déclenche lors de la connexion d'un super admin)
    """
    if instance.profil == 'super_admin' and instance.is_active:
        try:
            # Supprimer les brouillons de plus de 7 jours
            date_limite = datetime.now() - timedelta(days=7)
            
            factures_a_supprimer = Facture.objects.filter(
                statut='brouillon',
                date_creation__lt=date_limite
            )
            
            count = factures_a_supprimer.count()
            if count > 0:
                factures_a_supprimer.delete()
                logger.info(f"Nettoyage automatique: {count} factures brouillons supprimées")
                
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des factures brouillons: {e}")


# Vérification des factures en retard (à appeler périodiquement)
def verifier_factures_en_retard():
    """
    Fonction utilitaire pour vérifier les factures en retard
    À appeler via une tâche cron ou Celery
    """
    try:
        factures_retard = Facture.objects.filter(
            statut='emise',
            date_echeance__lt=datetime.now().date()
        ).select_related('client', 'reservation')
        
        if factures_retard.exists():
            # Notifier les gestionnaires
            gestionnaires = User.objects.filter(
                profil__in=['gestionnaire', 'super_admin'],
                is_active=True,
                email__isnull=False
            ).exclude(email='')
            
            if gestionnaires.exists():
                sujet = f"RepAvi - {factures_retard.count()} facture(s) en retard"
                
                contexte = {
                    'factures_retard': factures_retard,
                    'count': factures_retard.count(),
                }
                
                message_html = render_to_string('facturation/emails/factures_retard.html', contexte)
                message_text = strip_tags(message_html)
                
                emails_gestionnaires = [g.email for g in gestionnaires]
                
                send_mail(
                    subject=sujet,
                    message=message_text,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@repavilodges.com'),
                    recipient_list=emails_gestionnaires,
                    html_message=message_html,
                    fail_silently=True
                )
                
                logger.info(f"Alerte envoyée: {factures_retard.count()} factures en retard")
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des factures en retard: {e}")


# Configuration des signaux dans apps.py
def setup_signals():
    """
    Configure les signaux de l'application facturation
    """
    # Les signaux sont automatiquement enregistrés lors de l'import de ce module
    pass