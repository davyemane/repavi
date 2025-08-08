# apps/users/management/commands/create_superadmin.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import getpass

User = get_user_model()

class Command(BaseCommand):
    help = 'Créer un Super Administrateur pour RepAvi Lodges'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Nom d\'utilisateur du Super Admin'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email du Super Admin'
        )
        parser.add_argument(
            '--prenom',
            type=str,
            help='Prénom du Super Admin'
        )
        parser.add_argument(
            '--nom',
            type=str,
            help='Nom du Super Admin'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== Création d\'un Super Administrateur RepAvi Lodges ===')
        )
        
        # Récupérer les informations
        username = options['username'] or input('Nom d\'utilisateur: ')
        email = options['email'] or input('Email: ')
        first_name = options['prenom'] or input('Prénom: ')
        last_name = options['nom'] or input('Nom: ')
        
        # Vérifier l'unicité
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.ERROR(f'Erreur: Un utilisateur avec le nom "{username}" existe déjà.')
            )
            return
            
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f'Erreur: Un utilisateur avec l\'email "{email}" existe déjà.')
            )
            return

        # Mot de passe
        while True:
            password = getpass.getpass('Mot de passe: ')
            password_confirm = getpass.getpass('Confirmer le mot de passe: ')
            
            if password != password_confirm:
                self.stdout.write(
                    self.style.ERROR('Les mots de passe ne correspondent pas. Réessayez.')
                )
                continue
                
            if len(password) < 8:
                self.stdout.write(
                    self.style.ERROR('Le mot de passe doit contenir au moins 8 caractères.')
                )
                continue
                
            break

        # Créer le Super Admin
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                profil='super_admin',
                is_superuser=True,
                is_staff=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Super Administrateur créé avec succès !\n'
                    f'   Nom d\'utilisateur: {username}\n'
                    f'   Email: {email}\n'
                    f'   Nom complet: {first_name} {last_name}\n'
                    f'   Profil: Super Administrateur\n'
                    f'\n🔑 Il peut maintenant se connecter au système RepAvi Lodges.'
                )
            )
            
        except ValidationError as e:
            self.stdout.write(
                self.style.ERROR(f'Erreur lors de la création: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erreur inattendue: {e}')
            )