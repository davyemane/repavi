# reservations/management/commands/sync_reservations_maisons.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import date
from reservations.models import Reservation
from home.models import Maison
from django.db.models import Count

class Command(BaseCommand):
    help = 'Synchronise les réservations avec l\'occupation des maisons'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simule les changements sans les appliquer',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force la synchronisation même en cas de conflits',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Début de la synchronisation réservations/maisons'))
        
        dry_run = options['dry_run']
        force = options['force']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ Mode simulation activé - aucun changement ne sera appliqué'))
        
        total_corrections = 0
        total_erreurs = 0
        
        # 1. Synchroniser les réservations confirmées
        total_corrections += self._sync_reservations_confirmees(dry_run, force)
        
        # 2. Libérer les maisons pour réservations terminées/annulées
        total_corrections += self._sync_reservations_terminees(dry_run, force)
        
        # 3. Vérifier les maisons occupées sans réservation valide
        total_corrections += self._sync_maisons_orphelines(dry_run, force)
        
        # 4. Corriger les réservations en retard
        total_corrections += self._sync_reservations_retard(dry_run, force)
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Simulation terminée: {total_corrections} corrections identifiées')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Synchronisation terminée: {total_corrections} corrections appliquées')
            )
            
        if total_erreurs > 0:
            self.stdout.write(
                self.style.ERROR(f'❌ {total_erreurs} erreurs rencontrées')
            )

    def _sync_reservations_confirmees(self, dry_run, force):
        """Synchronise les réservations confirmées avec l'occupation des maisons"""
        self.stdout.write('🔍 Vérification des réservations confirmées...')
        
        corrections = 0
        today = timezone.now().date()
        
        # Réservations confirmées en cours ou futures
        reservations_confirmees = Reservation.objects.filter(
            statut='confirmee',
            date_fin__gte=today
        ).select_related('maison', 'client')
        
        for reservation in reservations_confirmees:
            maison = reservation.maison
            client = reservation.client
            
            # Vérifier si la maison est correctement occupée
            if maison.statut_occupation != 'occupe' or maison.locataire_actuel != client:
                self.stdout.write(
                    f'⚠️ Incohérence détectée:'
                    f'\n   Réservation: {reservation.numero} (confirmée)'
                    f'\n   Maison: {maison.nom} (statut: {maison.statut_occupation})'
                    f'\n   Attendu: occupée par {client.get_full_name()}'
                    f'\n   Actuel: {maison.locataire_actuel.get_full_name() if maison.locataire_actuel else "libre"}'
                )
                
                if not dry_run:
                    try:
                        with transaction.atomic():
                            maison.occuper_maison(client, reservation.date_fin)
                            self.stdout.write(
                                self.style.SUCCESS(f'✅ Maison {maison.nom} occupée par {client.get_full_name()}')
                            )
                            corrections += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'❌ Erreur lors de l\'occupation: {e}')
                        )
                else:
                    corrections += 1
        
        return corrections

    def _sync_reservations_terminees(self, dry_run, force):
        """Libère les maisons pour les réservations terminées ou annulées"""
        self.stdout.write('🔍 Vérification des réservations terminées/annulées...')
        
        corrections = 0
        today = timezone.now().date()
        
        # Réservations terminées ou annulées mais maison encore occupée
        reservations_finies = Reservation.objects.filter(
            statut__in=['terminee', 'annulee']
        ).select_related('maison', 'client')
        
        for reservation in reservations_finies:
            maison = reservation.maison
            client = reservation.client
            
            # Si la maison est encore occupée par ce client
            if (maison.statut_occupation == 'occupe' and 
                maison.locataire_actuel == client):
                
                self.stdout.write(
                    f'⚠️ Maison encore occupée pour réservation {reservation.statut}:'
                    f'\n   Réservation: {reservation.numero} ({reservation.statut})'
                    f'\n   Maison: {maison.nom} (occupée par {client.get_full_name()})'
                )
                
                if not dry_run:
                    try:
                        with transaction.atomic():
                            maison.liberer_maison()
                            self.stdout.write(
                                self.style.SUCCESS(f'✅ Maison {maison.nom} libérée')
                            )
                            corrections += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'❌ Erreur lors de la libération: {e}')
                        )
                else:
                    corrections += 1
        
        # Réservations confirmées expirées
        reservations_expirees = Reservation.objects.filter(
            statut='confirmee',
            date_fin__lt=today
        ).select_related('maison', 'client')
        
        for reservation in reservations_expirees:
            maison = reservation.maison
            client = reservation.client
            
            self.stdout.write(
                f'⚠️ Réservation expirée non terminée:'
                f'\n   Réservation: {reservation.numero} (fin: {reservation.date_fin})'
                f'\n   Maison: {maison.nom}'
            )
            
            if not dry_run:
                try:
                    with transaction.atomic():
                        # Terminer automatiquement la réservation
                        reservation.terminer()
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Réservation {reservation.numero} terminée automatiquement')
                        )
                        corrections += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Erreur lors de la terminaison: {e}')
                    )
            else:
                corrections += 1
        
        return corrections

    def _sync_maisons_orphelines(self, dry_run, force):
        """Vérifie les maisons occupées sans réservation valide"""
        self.stdout.write('🔍 Vérification des maisons orphelines...')
        
        corrections = 0
        today = timezone.now().date()
        
        # Maisons marquées comme occupées
        maisons_occupees = Maison.objects.filter(
            statut_occupation='occupe',
            locataire_actuel__isnull=False
        ).select_related('locataire_actuel')
        
        for maison in maisons_occupees:
            client = maison.locataire_actuel
            
            # Chercher une réservation confirmée valide
            reservation_valide = Reservation.objects.filter(
                maison=maison,
                client=client,
                statut='confirmee',
                date_debut__lte=today,
                date_fin__gte=today
            ).first()
            
            if not reservation_valide:
                self.stdout.write(
                    f'⚠️ Maison orpheline détectée:'
                    f'\n   Maison: {maison.nom} (occupée par {client.get_full_name()})'
                    f'\n   Aucune réservation confirmée valide trouvée'
                )
                
                if not dry_run:
                    try:
                        with transaction.atomic():
                            maison.liberer_maison()
                            self.stdout.write(
                                self.style.SUCCESS(f'✅ Maison orpheline {maison.nom} libérée')
                            )
                            corrections += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'❌ Erreur lors de la libération: {e}')
                        )
                else:
                    corrections += 1
        
        return corrections

    def _sync_reservations_retard(self, dry_run, force):
        """Gère les réservations en retard de traitement"""
        self.stdout.write('🔍 Vérification des réservations en retard...')
        
        corrections = 0
        today = timezone.now().date()
        
        # Réservations en attente depuis plus de 7 jours
        from datetime import timedelta
        seuil_retard = timezone.now() - timedelta(days=7)
        
        reservations_retard = Reservation.objects.filter(
            statut='en_attente',
            date_creation__lt=seuil_retard
        ).select_related('maison', 'client')
        
        for reservation in reservations_retard:
            jours_retard = (timezone.now() - reservation.date_creation).days
            
            self.stdout.write(
                f'⚠️ Réservation en retard:'
                f'\n   Réservation: {reservation.numero} ({jours_retard} jours en attente)'
                f'\n   Client: {reservation.client.get_full_name()}'
                f'\n   Maison: {reservation.maison.nom}'
            )
            
            # Si la date de début est dépassée, annuler automatiquement
            if reservation.date_debut < today:
                if not dry_run:
                    try:
                        with transaction.atomic():
                            reservation.annuler(
                                f"Annulée automatiquement - en attente depuis {jours_retard} jours et date de début dépassée"
                            )
                            self.stdout.write(
                                self.style.SUCCESS(f'✅ Réservation {reservation.numero} annulée automatiquement')
                            )
                            corrections += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'❌ Erreur lors de l\'annulation: {e}')
                        )
                else:
                    corrections += 1
        
        return corrections

    def _afficher_rapport_final(self):
        """Affiche un rapport final de la synchronisation"""
        self.stdout.write(self.style.SUCCESS('\n📊 RAPPORT DE SYNCHRONISATION'))
        self.stdout.write('=' * 50)
        
        # Statistiques globales
        total_reservations = Reservation.objects.count()
        reservations_confirmees = Reservation.objects.filter(statut='confirmee').count()
        maisons_occupees = Maison.objects.filter(statut_occupation='occupe').count()
        
        self.stdout.write(f'📈 Total réservations: {total_reservations}')
        self.stdout.write(f'✅ Réservations confirmées: {reservations_confirmees}')
        self.stdout.write(f'🏠 Maisons occupées: {maisons_occupees}')
        
        # Répartition par statut
        statuts = Reservation.objects.values('statut').annotate(
            count=Count('id')
        ).order_by('-count')
        
        self.stdout.write('\n📊 Répartition par statut:')
        for statut in statuts:
            self.stdout.write(f'   {statut["statut"]}: {statut["count"]}')

# Utilisation:
# python manage.py sync_reservations_maisons --dry-run  # Simulation
# python manage.py sync_reservations_maisons           # Application réelle
# python manage.py sync_reservations_maisons --force   # Force en cas de conflits