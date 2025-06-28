
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

from .models import Reservation, Paiement, EvaluationReservation


@receiver(pre_save, sender=Reservation)
def reservation_pre_save(sender, instance, **kwargs):
    """Actions avant la sauvegarde d'une réservation"""
    
    # Si c'est une nouvelle réservation
    if not instance.pk:
        # Générer le numéro automatiquement s'il n'existe pas
        if not instance.numero:
            instance.numero = Reservation.objects.generate_numero()
        
        # Définir le prix par nuit au moment de la réservation
        if not instance.prix_par_nuit and instance.maison:
            instance.prix_par_nuit = instance.maison.prix_par_nuit
    
    # Calculer automatiquement les totaux
    if instance.date_debut and instance.date_fin:
        instance.nombre_nuits = (instance.date_fin - instance.date_debut).days


@receiver(post_save, sender=Reservation)
def reservation_post_save(sender, instance, created, **kwargs):
    """Actions après la sauvegarde d'une réservation"""
    
    if created:
        # Nouvelle réservation créée
        _send_reservation_confirmation_email(instance)
        _notify_gestionnaire_new_reservation(instance)
        
        # Mettre à jour le statut d'occupation de la maison si confirmée
        if instance.statut == 'confirmee':
            instance.maison.occuper_maison(instance.client, instance.date_fin)
    
    else:
        # Réservation modifiée - vérifier les changements de statut
        try:
            # Récupérer l'ancienne version depuis la base
            old_instance = Reservation.objects.get(pk=instance.pk)
            
            # Détecter les changements de statut
            if old_instance.statut != instance.statut:
                _handle_status_change(old_instance, instance)
                
        except Reservation.DoesNotExist:
            pass


@receiver(post_delete, sender=Reservation)
def reservation_post_delete(sender, instance, **kwargs):
    """Actions après la suppression d'une réservation"""
    
    # Libérer la maison si elle était occupée par cette réservation
    if instance.statut == 'confirmee' and instance.maison.locataire_actuel == instance.client:
        instance.maison.liberer_maison()


@receiver(post_save, sender=Paiement)
def paiement_post_save(sender, instance, created, **kwargs):
    """Actions après la sauvegarde d'un paiement"""
    
    if created:
        # Nouveau paiement créé
        _send_payment_confirmation_email(instance)
        _notify_gestionnaire_new_payment(instance)
    
    else:
        # Paiement modifié - vérifier les changements de statut
        try:
            old_instance = Paiement.objects.get(pk=instance.pk)
            
            if old_instance.statut != instance.statut:
                if instance.statut == 'valide':
                    _handle_payment_validated(instance)
                elif instance.statut == 'echec':
                    _handle_payment_failed(instance)
                    
        except Paiement.DoesNotExist:
            pass


@receiver(post_save, sender=EvaluationReservation)
def evaluation_post_save(sender, instance, created, **kwargs):
    """Actions après la sauvegarde d'une évaluation"""
    
    if created:
        # Nouvelle évaluation créée
        _notify_gestionnaire_new_evaluation(instance)
    
    else:
        # Évaluation modifiée - vérifier si une réponse a été ajoutée
        try:
            old_instance = EvaluationReservation.objects.get(pk=instance.pk)
            
            if not old_instance.reponse_gestionnaire and instance.reponse_gestionnaire:
                _notify_client_evaluation_response(instance)
                
        except EvaluationReservation.DoesNotExist:
            pass


# ======== FONCTIONS HELPER POUR LES NOTIFICATIONS ========

def _send_reservation_confirmation_email(reservation):
    """Envoie un email de confirmation de réservation au client"""
    try:
        subject = f"Confirmation de réservation - {reservation.numero}"
        
        # TODO: Utiliser un template HTML
        message = f"""
        Bonjour {reservation.client.first_name},
        
        Votre réservation a été créée avec succès !
        
        Détails de la réservation :
        - Numéro : {reservation.numero}
        - Maison : {reservation.maison.nom}
        - Période : du {reservation.date_debut.strftime('%d/%m/%Y')} au {reservation.date_fin.strftime('%d/%m/%Y')}
        - Nombre de nuits : {reservation.nombre_nuits}
        - Nombre de personnes : {reservation.nombre_personnes}
        - Prix total : {reservation.prix_total:,.0f} FCFA
        - Statut : {reservation.get_statut_display()}
        
        Vous recevrez une notification lorsque votre réservation sera confirmée par le gestionnaire.
        
        Cordialement,
        L'équipe RepAvi Lodges
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [reservation.client.email],
            fail_silently=True,
        )
        
    except Exception as e:
        print(f"Erreur envoi email confirmation réservation: {e}")


def _notify_gestionnaire_new_reservation(reservation):
    """Notifie le gestionnaire d'une nouvelle réservation"""
    try:
        subject = f"Nouvelle réservation - {reservation.numero}"
        
        message = f"""
        Nouvelle réservation reçue !
        
        Client : {reservation.client.get_full_name()} ({reservation.client.email})
        Maison : {reservation.maison.nom}
        Période : du {reservation.date_debut.strftime('%d/%m/%Y')} au {reservation.date_fin.strftime('%d/%m/%Y')}
        Nombre de personnes : {reservation.nombre_personnes}
        Prix total : {reservation.prix_total:,.0f} FCFA
        
        Connectez-vous à votre espace gestionnaire pour confirmer cette réservation.
        
        RepAvi Lodges
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [reservation.maison.gestionnaire.email],
            fail_silently=True,
        )
        
    except Exception as e:
        print(f"Erreur notification gestionnaire nouvelle réservation: {e}")


def _handle_status_change(old_reservation, new_reservation):
    """Gère les changements de statut de réservation"""
    
    if new_reservation.statut == 'confirmee' and old_reservation.statut == 'en_attente':
        # Réservation confirmée
        _send_reservation_confirmed_email(new_reservation)
        
        # Occuper la maison
        new_reservation.maison.occuper_maison(
            new_reservation.client, 
            new_reservation.date_fin
        )
        
    elif new_reservation.statut == 'annulee':
        # Réservation annulée
        _send_reservation_cancelled_email(new_reservation)
        
        # Libérer la maison si elle était occupée
        if old_reservation.statut == 'confirmee':
            new_reservation.maison.liberer_maison()
            
    elif new_reservation.statut == 'terminee' and old_reservation.statut == 'confirmee':
        # Séjour terminé
        _send_stay_completed_email(new_reservation)
        
        # Libérer la maison
        new_reservation.maison.liberer_maison()
        
        # Programmer la demande d'évaluation (après 24h)
        # TODO: Utiliser Celery pour programmer la tâche


def _send_reservation_confirmed_email(reservation):
    """Envoie un email de confirmation de réservation"""
    try:
        subject = f"Réservation confirmée - {reservation.numero}"
        
        message = f"""
        Excellente nouvelle ! Votre réservation a été confirmée.
        
        Détails de votre séjour :
        - Numéro : {reservation.numero}
        - Maison : {reservation.maison.nom}
        - Adresse : {reservation.maison.adresse}, {reservation.maison.ville.nom}
        - Arrivée : {reservation.date_debut.strftime('%d/%m/%Y')} à {reservation.heure_arrivee or '15:00'}
        - Départ : {reservation.date_fin.strftime('%d/%m/%Y')} à {reservation.heure_depart or '11:00'}
        
        Contact du gestionnaire : {reservation.maison.gestionnaire.email}
        
        Nous vous souhaitons un excellent séjour !
        
        L'équipe RepAvi Lodges
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [reservation.client.email],
            fail_silently=True,
        )
        
    except Exception as e:
        print(f"Erreur envoi email confirmation: {e}")


def _send_reservation_cancelled_email(reservation):
    """Envoie un email d'annulation de réservation"""
    try:
        subject = f"Réservation annulée - {reservation.numero}"
        
        message = f"""
        Votre réservation a été annulée.
        
        Détails :
        - Numéro : {reservation.numero}
        - Maison : {reservation.maison.nom}
        - Période : du {reservation.date_debut.strftime('%d/%m/%Y')} au {reservation.date_fin.strftime('%d/%m/%Y')}
        - Raison : {reservation.raison_annulation}
        
        Si vous avez effectué un paiement, notre équipe vous contactera pour le remboursement.
        
        L'équipe RepAvi Lodges
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [reservation.client.email],
            fail_silently=True,
        )
        
    except Exception as e:
        print(f"Erreur envoi email annulation: {e}")


def _send_stay_completed_email(reservation):
    """Envoie un email de fin de séjour"""
    try:
        subject = f"Merci pour votre séjour - {reservation.numero}"
        
        # TODO: Inclure un lien vers le formulaire d'évaluation
        message = f"""
        Merci d'avoir choisi RepAvi Lodges !
        
        Nous espérons que vous avez passé un excellent séjour à {reservation.maison.nom}.
        
        Nous serions ravis de connaître votre avis sur votre expérience.
        Votre évaluation nous aide à améliorer nos services.
        
        À bientôt pour un prochain séjour !
        
        L'équipe RepAvi Lodges
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [reservation.client.email],
            fail_silently=True,
        )
        
    except Exception as e:
        print(f"Erreur envoi email fin séjour: {e}")


def _send_payment_confirmation_email(paiement):
    """Envoie un email de confirmation de paiement"""
    try:
        subject = f"Confirmation de paiement - {paiement.numero_transaction}"
        
        message = f"""
        Votre paiement a été enregistré.
        
        Détails :
        - Numéro de transaction : {paiement.numero_transaction}
        - Réservation : {paiement.reservation.numero}
        - Montant : {paiement.montant:,.0f} FCFA
        - Type de paiement : {paiement.type_paiement.nom}
        - Statut : {paiement.get_statut_display()}
        
        Vous recevrez une notification une fois le paiement validé.
        
        L'équipe RepAvi Lodges
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [paiement.reservation.client.email],
            fail_silently=True,
        )
        
    except Exception as e:
        print(f"Erreur envoi email paiement: {e}")


def _notify_gestionnaire_new_payment(paiement):
    """Notifie le gestionnaire d'un nouveau paiement"""
    try:
        subject = f"Nouveau paiement - {paiement.numero_transaction}"
        
        message = f"""
        Nouveau paiement reçu pour la réservation {paiement.reservation.numero}.
        
        Client : {paiement.reservation.client.get_full_name()}
        Montant : {paiement.montant:,.0f} FCFA
        Type : {paiement.type_paiement.nom}
        
        Connectez-vous pour valider ce paiement.
        
        RepAvi Lodges
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [paiement.reservation.maison.gestionnaire.email],
            fail_silently=True,
        )
        
    except Exception as e:
        print(f"Erreur notification gestionnaire paiement: {e}")


def _handle_payment_validated(paiement):
    """Gère la validation d'un paiement"""
    try:
        subject = f"Paiement validé - {paiement.numero_transaction}"
        
        # Calculer le montant restant
        montant_total_paye = paiement.reservation.paiements.filter(
            statut='valide'
        ).aggregate(total=models.Sum('montant'))['total'] or 0
        
        montant_restant = paiement.reservation.prix_total - montant_total_paye
        
        message = f"""
        Votre paiement a été validé avec succès !
        
        Détails :
        - Numéro de transaction : {paiement.numero_transaction}
        - Montant validé : {paiement.montant:,.0f} FCFA
        - Montant restant : {montant_restant:,.0f} FCFA
        
        {"Votre réservation est entièrement payée !" if montant_restant <= 0 else ""}
        
        L'équipe RepAvi Lodges
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [paiement.reservation.client.email],
            fail_silently=True,
        )
        
    except Exception as e:
        print(f"Erreur notification paiement validé: {e}")


def _handle_payment_failed(paiement):
    """Gère l'échec d'un paiement"""
    try:
        subject = f"Échec de paiement - {paiement.numero_transaction}"
        
        message = f"""
        Votre paiement n'a pas pu être traité.
        
        Détails :
        - Numéro de transaction : {paiement.numero_transaction}
        - Montant : {paiement.montant:,.0f} FCFA
        
        Veuillez réessayer ou contacter notre équipe pour assistance.
        
        L'équipe RepAvi Lodges
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [paiement.reservation.client.email],
            fail_silently=True,
        )
        
    except Exception as e:
        print(f"Erreur notification échec paiement: {e}")


def _notify_gestionnaire_new_evaluation(evaluation):
    """Notifie le gestionnaire d'une nouvelle évaluation"""
    try:
        subject = f"Nouvelle évaluation - {evaluation.reservation.numero}"
        
        message = f"""
        Une nouvelle évaluation a été laissée pour votre maison {evaluation.reservation.maison.nom}.
        
        Client : {evaluation.reservation.client.get_full_name()}
        Note globale : {evaluation.note_globale}/5 étoiles
        
        Commentaire : "{evaluation.commentaire[:200]}..."
        
        Connectez-vous pour consulter l'évaluation complète et y répondre.
        
        RepAvi Lodges
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [evaluation.reservation.maison.gestionnaire.email],
            fail_silently=True,
        )
        
    except Exception as e:
        print(f"Erreur notification nouvelle évaluation: {e}")


def _notify_client_evaluation_response(evaluation):
    """Notifie le client qu'une réponse a été donnée à son évaluation"""
    try:
        subject = f"Réponse à votre évaluation - {evaluation.reservation.maison.nom}"
        
        message = f"""
        Le gestionnaire de {evaluation.reservation.maison.nom} a répondu à votre évaluation.
        
        Sa réponse :
        "{evaluation.reponse_gestionnaire}"
        
        Merci pour votre retour qui nous aide à améliorer nos services !
        
        L'équipe RepAvi Lodges
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [evaluation.reservation.client.email],
            fail_silently=True,
        )
        
    except Exception as e:
        print(f"Erreur notification réponse évaluation: {e}")