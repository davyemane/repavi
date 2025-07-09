# management/commands/update_avis_statut.py
from django.core.management.base import BaseCommand
from avis.models import Avis

class Command(BaseCommand):
    help = 'Met à jour le statut de modération des avis existants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--approve-all',
            action='store_true',
            help='Approuve tous les avis existants',
        )

    def handle(self, *args, **options):
        if options['approve_all']:
            # Approuver tous les avis existants
            updated = Avis.objects.filter(
                statut_moderation='en_attente'
            ).update(statut_moderation='approuve')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated {updated} avis to "approuve" status'
                )
            )
        else:
            # Afficher les statistiques
            en_attente = Avis.objects.filter(statut_moderation='en_attente').count()
            approuve = Avis.objects.filter(statut_moderation='approuve').count()
            rejete = Avis.objects.filter(statut_moderation='rejete').count()
            
            self.stdout.write(f"Avis en attente: {en_attente}")
            self.stdout.write(f"Avis approuvés: {approuve}")
            self.stdout.write(f"Avis rejetés: {rejete}")
            
            self.stdout.write(
                "Utilisez --approve-all pour approuver tous les avis en attente"
            )

# Utilisation :
# python manage.py update_avis_statut --approve-all