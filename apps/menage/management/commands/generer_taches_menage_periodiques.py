from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.appartements.models import Appartement
from apps.menage.models import TacheMenage


class Command(BaseCommand):
    help = 'Génère des tâches de ménage tous les 2 jours pour tous les appartements'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Date de la prochaine tâche (dans 2 jours)
        date_tache = today + timedelta(days=2)
        
        appartements = Appartement.objects.all()
        taches_creees = 0
        taches_existantes = 0
        
        for appartement in appartements:
            # Créer tâche uniquement si elle n'existe pas déjà pour cette date
            tache, created = TacheMenage.objects.get_or_create(
                appartement=appartement,
                date_prevue=date_tache,
                defaults={
                    'statut': 'a_faire'
                }
            )
            
            if created:
                taches_creees += 1
            else:
                taches_existantes += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Tâches créées: {taches_creees} | '
                f'Déjà existantes: {taches_existantes} | '
                f'Date prévue: {date_tache}'
            )
        )