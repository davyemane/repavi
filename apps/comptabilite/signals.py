# apps/comptabilite/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.paiements.models import EcheancierPaiement
from apps.inventaire.models import EquipementAppartement
from .models import ComptabiliteAppartement
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=EcheancierPaiement)
def creer_revenu_apres_paiement(sender, instance, created, **kwargs):
    """REVENUS : Mouvement automatique après paiement"""
    
    if instance.statut != 'paye':
        return
        
    if not instance.reservation or not instance.reservation.appartement:
        logger.warning(f"Paiement {instance.id} sans réservation/appartement")
        return
    
    # Éviter doublons
    if ComptabiliteAppartement.objects.filter(
        reservation=instance.reservation,
        type_mouvement='revenu',
        montant=instance.montant_paye,
        date_mouvement=instance.date_paiement,
        libelle__contains=f'Paiement #{instance.id}'
    ).exists():
        return
    
    try:
        ComptabiliteAppartement.objects.create(
            appartement=instance.reservation.appartement,
            reservation=instance.reservation,
            type_mouvement='revenu',
            libelle=f'{instance.get_type_paiement_display()} - {instance.reservation.client.prenom} {instance.reservation.client.nom} - Paiement #{instance.id}',
            montant=instance.montant_paye,
            date_mouvement=instance.date_paiement
        )
        logger.info(f"Revenu créé: {instance.reservation.appartement.numero} - {instance.montant_paye} FCFA")
        
    except Exception as e:
        logger.error(f"Erreur création revenu: {e}")


@receiver(post_save, sender=EquipementAppartement)
def creer_charge_equipement_defectueux(sender, instance, created, **kwargs):
    """CHARGES : Mouvement automatique pour équipements défectueux/hors service"""
    
    # Seulement pour équipements problématiques
    if instance.etat not in ['defectueux', 'hors_service']:
        return
    
    # Éviter doublons
    if ComptabiliteAppartement.objects.filter(
        appartement=instance.appartement,
        type_mouvement='charge',
        libelle__contains=f'Équipement #{instance.id}',
        date_mouvement=instance.date_modification.date()
    ).exists():
        return
    
    # Calculer coût selon état
    if instance.etat == 'defectueux':
        # Coût réparation = 20% du prix d'achat
        montant_charge = instance.prix_achat * 0.20
        libelle = f'Réparation {instance.nom} - Équipement #{instance.id}'
    else:  # hors_service
        # Coût remplacement = 80% du prix d'achat
        montant_charge = instance.prix_achat * 0.80
        libelle = f'Remplacement {instance.nom} - Équipement #{instance.id}'
    
    try:
        ComptabiliteAppartement.objects.create(
            appartement=instance.appartement,
            type_mouvement='charge',
            libelle=libelle,
            montant=montant_charge,
            date_mouvement=instance.date_modification.date()
        )
        logger.info(f"Charge créée: {instance.appartement.numero} - {montant_charge} FCFA ({instance.etat})")
        
    except Exception as e:
        logger.error(f"Erreur création charge équipement: {e}")