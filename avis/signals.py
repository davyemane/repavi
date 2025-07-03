# avis/signals.py
"""
Signals pour l'app avis - Actions automatiques lors d'événements
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Avis, LikeAvis, SignalementAvis, PhotoAvis


@receiver(post_save, sender=Avis)
def avis_post_save_handler(sender, instance, created, **kwargs):
    """Actions après sauvegarde d'un avis"""
    
    if created:
        # Nouvel avis créé
        print(f"Nouvel avis créé : {instance.id} par {instance.client.nom_complet}")
        
        # 1. Envoyer notification au gestionnaire de la maison
        gestionnaire = instance.maison.gestionnaire
        if gestionnaire and gestionnaire.notifications_email:
            try:
                sujet = f"Nouvel avis pour {instance.maison.nom}"
                contexte = {
                    'avis': instance,
                    'maison': instance.maison,
                    'gestionnaire': gestionnaire,
                    'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000')
                }
                
                # Email HTML
                message_html = render_to_string('avis/emails/nouvel_avis_gestionnaire.html', contexte)
                message_text = render_to_string('avis/emails/nouvel_avis_gestionnaire.txt', contexte)
                
                send_mail(
                    subject=sujet,
                    message=message_text,
                    html_message=message_html,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[gestionnaire.email],
                    fail_silently=True
                )
                print(f"Email envoyé au gestionnaire {gestionnaire.email}")
                
            except Exception as e:
                print(f"Erreur envoi email gestionnaire: {e}")
        
        # 2. Notification admin si avis nécessite modération
        if instance.statut_moderation == 'en_attente':
            try:
                # Envoyer notification aux super admins
                from users.models import User
                super_admins = User.objects.filter(
                    role='SUPER_ADMIN',
                    notifications_email=True,
                    is_active=True
                )
                
                if super_admins.exists():
                    sujet = f"Avis en attente de modération - {instance.maison.nom}"
                    contexte = {
                        'avis': instance,
                        'maison': instance.maison,
                        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000')
                    }
                    
                    message_html = render_to_string('avis/emails/avis_moderation_admin.html', contexte)
                    message_text = render_to_string('avis/emails/avis_moderation_admin.txt', contexte)
                    
                    emails_admins = list(super_admins.values_list('email', flat=True))
                    
                    send_mail(
                        subject=sujet,
                        message=message_text,
                        html_message=message_html,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=emails_admins,
                        fail_silently=True
                    )
                    print(f"Email modération envoyé aux admins: {emails_admins}")
                    
            except Exception as e:
                print(f"Erreur envoi email admin: {e}")
    
    else:
        # Avis modifié
        if instance.statut_moderation == 'approuve':
            # Avis approuvé - notifier le client
            try:
                client = instance.client
                if client.notifications_email:
                    sujet = f"Votre avis a été publié - {instance.maison.nom}"
                    contexte = {
                        'avis': instance,
                        'maison': instance.maison,
                        'client': client,
                        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000')
                    }
                    
                    message_html = render_to_string('avis/emails/avis_approuve_client.html', contexte)
                    message_text = render_to_string('avis/emails/avis_approuve_client.txt', contexte)
                    
                    send_mail(
                        subject=sujet,
                        message=message_text,
                        html_message=message_html,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[client.email],
                        fail_silently=True
                    )
                    print(f"Email approbation envoyé au client {client.email}")
                    
            except Exception as e:
                print(f"Erreur envoi email approbation: {e}")
        
        elif instance.statut_moderation == 'rejete':
            # Avis rejeté - notifier le client
            try:
                client = instance.client
                if client.notifications_email:
                    sujet = f"Votre avis nécessite une révision - {instance.maison.nom}"
                    contexte = {
                        'avis': instance,
                        'maison': instance.maison,
                        'client': client,
                        'raison_rejet': instance.raison_rejet,
                        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000')
                    }
                    
                    message_html = render_to_string('avis/emails/avis_rejete_client.html', contexte)
                    message_text = render_to_string('avis/emails/avis_rejete_client.txt', contexte)
                    
                    send_mail(
                        subject=sujet,
                        message=message_text,
                        html_message=message_html,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[client.email],
                        fail_silently=True
                    )
                    print(f"Email rejet envoyé au client {client.email}")
                    
            except Exception as e:
                print(f"Erreur envoi email rejet: {e}")
        
        # Nouvelle réponse du gestionnaire
        if instance.reponse_gestionnaire and instance.reponse_par:
            try:
                client = instance.client
                if client.notifications_email:
                    sujet = f"Réponse à votre avis - {instance.maison.nom}"
                    contexte = {
                        'avis': instance,
                        'maison': instance.maison,
                        'client': client,
                        'gestionnaire': instance.reponse_par,
                        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000')
                    }
                    
                    message_html = render_to_string('avis/emails/reponse_gestionnaire_client.html', contexte)
                    message_text = render_to_string('avis/emails/reponse_gestionnaire_client.txt', contexte)
                    
                    send_mail(
                        subject=sujet,
                        message=message_text,
                        html_message=message_html,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[client.email],
                        fail_silently=True
                    )
                    print(f"Email réponse gestionnaire envoyé au client {client.email}")
                    
            except Exception as e:
                print(f"Erreur envoi email réponse: {e}")


@receiver(post_save, sender=LikeAvis)
def like_avis_created_handler(sender, instance, created, **kwargs):
    """Mettre à jour le compteur de likes après création"""
    if created:
        avis = instance.avis
        # Recalculer le nombre de likes
        nouveau_count = avis.likes.count()
        if avis.nombre_likes != nouveau_count:
            Avis.objects.filter(pk=avis.pk).update(nombre_likes=nouveau_count)
            print(f"Avis {avis.id}: likes mis à jour ({nouveau_count})")


@receiver(post_delete, sender=LikeAvis)
def like_avis_deleted_handler(sender, instance, **kwargs):
    """Mettre à jour le compteur de likes après suppression"""
    avis = instance.avis
    # Recalculer le nombre de likes
    nouveau_count = avis.likes.count()
    if avis.nombre_likes != nouveau_count:
        Avis.objects.filter(pk=avis.pk).update(nombre_likes=nouveau_count)
        print(f"Avis {avis.id}: likes mis à jour après suppression ({nouveau_count})")


@receiver(post_save, sender=SignalementAvis)
def signalement_avis_created_handler(sender, instance, created, **kwargs):
    """Gérer les signalements d'avis"""
    if created:
        avis = instance.avis
        
        # Mettre à jour le compteur de signalements
        nouveau_count = avis.signalements.count()
        avis.nombre_signalements = nouveau_count
        
        # Auto-modération si trop de signalements
        if nouveau_count >= 5 and avis.statut_moderation == 'approuve':
            avis.statut_moderation = 'signale'
            print(f"Avis {avis.id} automatiquement marqué comme signalé ({nouveau_count} signalements)")
            
            # Notifier les admins d'un avis auto-signalé
            try:
                from users.models import User
                super_admins = User.objects.filter(
                    role='SUPER_ADMIN',
                    notifications_email=True,
                    is_active=True
                )
                
                if super_admins.exists():
                    sujet = f"URGENT: Avis auto-signalé - {avis.maison.nom}"
                    contexte = {
                        'avis': avis,
                        'maison': avis.maison,
                        'nombre_signalements': nouveau_count,
                        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000')
                    }
                    
                    message_html = render_to_string('avis/emails/avis_auto_signale_admin.html', contexte)
                    message_text = render_to_string('avis/emails/avis_auto_signale_admin.txt', contexte)
                    
                    emails_admins = list(super_admins.values_list('email', flat=True))
                    
                    send_mail(
                        subject=sujet,
                        message=message_text,
                        html_message=message_html,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=emails_admins,
                        fail_silently=True
                    )
                    print(f"Email avis auto-signalé envoyé aux admins")
                    
            except Exception as e:
                print(f"Erreur envoi email auto-signalement: {e}")
        
        avis.save()
        print(f"Signalement créé pour avis {avis.id} par {instance.user.nom_complet}")


@receiver(post_save, sender=PhotoAvis)
def photo_avis_saved_handler(sender, instance, created, **kwargs):
    """Actions après ajout/modification d'une photo d'avis"""
    if created:
        print(f"Photo ajoutée à l'avis {instance.avis.id}")
        
        # Optionnel: vérifier que le nombre de photos ne dépasse pas la limite
        nb_photos = instance.avis.photos.count()
        if nb_photos > 5:
            print(f"ATTENTION: Avis {instance.avis.id} a {nb_photos} photos (limite: 5)")


@receiver(pre_save, sender=Avis)
def avis_pre_save_handler(sender, instance, **kwargs):
    """Actions avant sauvegarde d'un avis"""
    
    # Si c'est une modification d'avis existant
    if instance.pk:
        try:
            old_instance = Avis.objects.get(pk=instance.pk)
            
            # Détecter changement de statut de modération
            if old_instance.statut_moderation != instance.statut_moderation:
                print(f"Avis {instance.id}: changement statut {old_instance.statut_moderation} → {instance.statut_moderation}")
                
                # Marquer la date de modération si passage en approuvé/rejeté
                if instance.statut_moderation in ['approuve', 'rejete'] and not instance.date_moderation:
                    instance.date_moderation = timezone.now()
            
            # Détecter ajout de réponse gestionnaire
            if not old_instance.reponse_gestionnaire and instance.reponse_gestionnaire:
                print(f"Nouvelle réponse gestionnaire pour avis {instance.id}")
                if not instance.date_reponse:
                    instance.date_reponse = timezone.now()
                    
        except Avis.DoesNotExist:
            pass


# Signal pour nettoyer les anciennes données (optionnel)
@receiver(post_delete, sender=Avis)
def avis_deleted_handler(sender, instance, **kwargs):
    """Nettoyage après suppression d'un avis"""
    print(f"Avis {instance.id} supprimé - nettoyage automatique")
    
    # Les photos, likes et signalements sont supprimés automatiquement via CASCADE
    # Mais on peut ajouter d'autres actions de nettoyage ici


# Fonction utilitaire pour envoyer des notifications groupées (tâche cron)
def envoyer_resume_quotidien_gestionnaires():
    """
    Fonction à appeler quotidiennement pour envoyer un résumé aux gestionnaires
    Peut être appelée via une tâche cron ou Celery
    """
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count
    from users.models import User
    
    hier = timezone.now() - timedelta(days=1)
    
    gestionnaires = User.objects.filter(
        role='GESTIONNAIRE',
        notifications_email=True,
        is_active=True
    )
    
    for gestionnaire in gestionnaires:
        # Compter les nouveaux avis depuis hier
        nouveaux_avis = Avis.objects.filter(
            maison__gestionnaire=gestionnaire,
            date_creation__gte=hier,
            statut_moderation='en_attente'
        ).count()
        
        avis_sans_reponse = Avis.objects.filter(
            maison__gestionnaire=gestionnaire,
            statut_moderation='approuve',
            reponse_gestionnaire='',
            date_creation__lte=timezone.now() - timedelta(days=2)  # Plus de 2 jours
        ).count()
        
        if nouveaux_avis > 0 or avis_sans_reponse > 0:
            try:
                sujet = f"Résumé quotidien - {nouveaux_avis} nouveaux avis à modérer"
                contexte = {
                    'gestionnaire': gestionnaire,
                    'nouveaux_avis': nouveaux_avis,
                    'avis_sans_reponse': avis_sans_reponse,
                    'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000')
                }
                
                message_html = render_to_string('avis/emails/resume_quotidien_gestionnaire.html', contexte)
                message_text = render_to_string('avis/emails/resume_quotidien_gestionnaire.txt', contexte)
                
                send_mail(
                    subject=sujet,
                    message=message_text,
                    html_message=message_html,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[gestionnaire.email],
                    fail_silently=True
                )
                print(f"Résumé quotidien envoyé à {gestionnaire.email}")
                
            except Exception as e:
                print(f"Erreur envoi résumé quotidien à {gestionnaire.email}: {e}")


# Configuration pour désactiver les signals en mode test
def disable_signals():
    """Désactiver les signals pour les tests"""
    post_save.disconnect(avis_post_save_handler, sender=Avis)
    post_save.disconnect(like_avis_created_handler, sender=LikeAvis)
    post_delete.disconnect(like_avis_deleted_handler, sender=LikeAvis)
    post_save.disconnect(signalement_avis_created_handler, sender=SignalementAvis)
    post_save.disconnect(photo_avis_saved_handler, sender=PhotoAvis)
    pre_save.disconnect(avis_pre_save_handler, sender=Avis)
    post_delete.disconnect(avis_deleted_handler, sender=Avis)


def enable_signals():
    """Réactiver les signals"""
    post_save.connect(avis_post_save_handler, sender=Avis)
    post_save.connect(like_avis_created_handler, sender=LikeAvis)
    post_delete.connect(like_avis_deleted_handler, sender=LikeAvis)
    post_save.connect(signalement_avis_created_handler, sender=SignalementAvis)
    post_save.connect(photo_avis_saved_handler, sender=PhotoAvis)
    pre_save.connect(avis_pre_save_handler, sender=Avis)
    post_delete.connect(avis_deleted_handler, sender=Avis)