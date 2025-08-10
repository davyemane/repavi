# python manage.py shell
from apps.paiements.models import EcheancierPaiement
from decimal import Decimal

# Corriger tous les soldes incorrects
for echeance in EcheancierPaiement.objects.filter(type_paiement='solde'):
    # Solde = 60% du prix total
    montant_correct = echeance.reservation.prix_total * Decimal('0.6')
    if echeance.montant_prevu != montant_correct:
        print(f"Correction résa #{echeance.reservation.pk}: {echeance.montant_prevu} → {montant_correct}")
        echeance.montant_prevu = montant_correct
        super(EcheancierPaiement, echeance).save()  # 