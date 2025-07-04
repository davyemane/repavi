# users/management/commands/fix_superusers.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Corriger les rôles des superutilisateurs existants'

    def handle(self, *args, **options):
        # Trouver tous les superutilisateurs avec un rôle CLIENT
        superusers_to_fix = User.objects.filter(
            is_superuser=True,
            role='CLIENT'
        )
        
        count = superusers_to_fix.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ Aucun superutilisateur à corriger trouvé.')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(f'🔍 {count} superutilisateur(s) trouvé(s) avec le rôle CLIENT')
        )
        
        # Afficher les utilisateurs qui seront modifiés
        for user in superusers_to_fix:
            self.stdout.write(f'  - {user.username} ({user.email})')
        
        # Demander confirmation
        confirm = input('\nVoulez-vous corriger ces utilisateurs ? (y/N): ')
        
        if confirm.lower() in ['y', 'yes', 'oui']:
            # Corriger les rôles
            updated = superusers_to_fix.update(role='SUPER_ADMIN')
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ {updated} superutilisateur(s) corrigé(s) avec le rôle SUPER_ADMIN')
            )
            
            # Afficher les utilisateurs corrigés
            for user in User.objects.filter(is_superuser=True, role='SUPER_ADMIN'):
                self.stdout.write(f'  ✓ {user.username} → SUPER_ADMIN')
        else:
            self.stdout.write(
                self.style.ERROR('❌ Opération annulée.')
            )