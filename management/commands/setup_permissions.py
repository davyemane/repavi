# home/management/commands/setup_permissions.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Configure les groupes et permissions selon le cahier technique RepAvi'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Configuration des permissions RepAvi...'))
        
        # Définition des permissions par rôle selon le cahier technique
        ROLE_PERMISSIONS = {
            'Client': [
                # Consultation et réservation
                'can_view_maisons',
                'can_make_reservation',
                'can_give_review',
                # Permissions Django de base pour son propre profil
                'change_user',  # Seulement son propre profil
            ],
            'Gestionnaire': [
                # Toutes les permissions client
                'can_view_maisons',
                'can_make_reservation',
                'can_give_review',
                # Gestion des entités
                'can_manage_clients',
                'can_manage_maisons',
                'can_manage_reservations',
                # Outils de gestion
                'can_generate_pdf',
                'can_view_statistics',
                # Permissions Django admin pour les modèles gérés
                'add_maison',
                'change_maison',
                'delete_maison',
                'view_maison',
                'add_reservation',
                'change_reservation',
                'delete_reservation',
                'view_reservation',
                'add_photomaison',
                'change_photomaison',
                'delete_photomaison',
                'view_photomaison',
                'view_user',
                'change_user',
            ],
            'Super Admin': [
                # Super Admin utilise is_superuser pour tout accès
                # Permissions spécifiques au système
                'can_manage_system',
                'can_create_gestionnaires',
                'can_modify_system_settings',
            ]
        }
        
        # Créer les groupes et assigner les permissions
        for group_name, permissions in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                self.stdout.write(f'✅ Groupe "{group_name}" créé')
            else:
                self.stdout.write(f'🔄 Groupe "{group_name}" existe déjà, mise à jour...')
            
            # Vider les permissions existantes
            group.permissions.clear()
            
            # Ajouter les nouvelles permissions
            permissions_added = 0
            for perm_codename in permissions:
                try:
                    permission = Permission.objects.get(codename=perm_codename)
                    group.permissions.add(permission)
                    permissions_added += 1
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Permission "{perm_codename}" non trouvée')
                    )
            
            self.stdout.write(f'  📝 {permissions_added} permissions ajoutées au groupe "{group_name}"')
        
        # Assigner automatiquement les utilisateurs existants aux groupes
        self.assign_users_to_groups()
        
        # Créer un super admin par défaut si aucun n'existe
        self.create_default_superuser()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Configuration des permissions terminée avec succès!')
        )
    
    def assign_users_to_groups(self):
        """Assigne automatiquement les utilisateurs existants aux bons groupes"""
        self.stdout.write('🔄 Attribution des utilisateurs aux groupes...')
        
        role_to_group = {
            'CLIENT': 'Client',
            'GESTIONNAIRE': 'Gestionnaire',
            'SUPER_ADMIN': 'Super Admin',
        }
        
        for role, group_name in role_to_group.items():
            try:
                group = Group.objects.get(name=group_name)
                users = User.objects.filter(role=role)
                
                for user in users:
                    user.groups.clear()  # Nettoie les anciens groupes
                    user.groups.add(group)
                
                count = users.count()
                self.stdout.write(f'  👥 {count} utilisateur(s) "{role}" assigné(s) au groupe "{group_name}"')
                
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Groupe "{group_name}" non trouvé')
                )
    
    def create_default_superuser(self):
        """Crée un super admin par défaut si aucun n'existe"""
        if not User.objects.filter(is_superuser=True).exists():
            self.stdout.write('🔧 Création d\'un super admin par défaut...')
            
            User.objects.create_superuser(
                username='admin',
                email='admin@repavi.com',
                password='admin123',
                first_name='Super',
                last_name='Admin',
                role='SUPER_ADMIN'
            )
            
            self.stdout.write(
                self.style.SUCCESS('✅ Super admin créé: admin / admin123')
            )
        else:
            self.stdout.write('ℹ️  Super admin déjà existant, aucune création nécessaire')
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Remet à zéro tous les groupes et permissions avant de les recréer',
        )