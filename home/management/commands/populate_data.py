# Commande pour créer des données de test
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from home.models import Ville, CategorieMaison, Maison
from decimal import Decimal

class Command(BaseCommand):
    help = 'Populate database with sample data'

    def handle(self, *args, **options):
        # Créer des villes
        villes_data = [
            {'nom': 'Paris', 'departement': 'Paris', 'code_postal': '75000'},
            {'nom': 'Nice', 'departement': 'Alpes-Maritimes', 'code_postal': '06000'},
            {'nom': 'Lyon', 'departement': 'Rhône', 'code_postal': '69000'},
            {'nom': 'Marseille', 'departement': 'Bouches-du-Rhône', 'code_postal': '13000'},
            {'nom': 'Chamonix', 'departement': 'Haute-Savoie', 'code_postal': '74400'},
        ]
        
        for ville_data in villes_data:
            ville, created = Ville.objects.get_or_create(**ville_data)
            if created:
                self.stdout.write(f'Ville créée: {ville.nom}')

        # Créer des catégories
        categories_data = [
            {'nom': 'Premium', 'couleur': 'blue', 'description': 'Maisons haut de gamme'},
            {'nom': 'Éco-friendly', 'couleur': 'green', 'description': 'Maisons écologiques'},
            {'nom': 'Centre-ville', 'couleur': 'purple', 'description': 'Maisons en centre-ville'},
            {'nom': 'Vue mer', 'couleur': 'cyan', 'description': 'Maisons avec vue sur mer'},
            {'nom': 'Montagne', 'couleur': 'orange', 'description': 'Chalets et maisons de montagne'},
        ]
        
        for cat_data in categories_data:
            categorie, created = CategorieMaison.objects.get_or_create(**cat_data)
            if created:
                self.stdout.write(f'Catégorie créée: {categorie.nom}')

        # Créer un utilisateur propriétaire
        proprietaire, created = User.objects.get_or_create(
            username='proprietaire',
            defaults={
                'email': 'proprietaire@maisonloc.com',
                'first_name': 'Propriétaire',
                'last_name': 'Test'
            }
        )

        # Créer des maisons exemple
        maisons_data = [
            {
                'nom': 'Villa Moderne Seaside',
                'description': 'Magnifique villa avec vue sur mer, entièrement meublée avec goût.',
                'adresse': '123 Boulevard de la Mer',
                'ville': Ville.objects.get(nom='Nice'),
                'capacite_personnes': 6,
                'nombre_chambres': 3,
                'nombre_salles_bain': 2,
                'superficie': 120,
                'prix_par_nuit': Decimal('180.00'),
                'categorie': CategorieMaison.objects.get(nom='Premium'),
                'featured': True,
                'proprietaire': proprietaire,
                'slug': 'villa-moderne-seaside',
                'wifi': True,
                'parking': True,
                'piscine': True,
            },
            {
                'nom': 'Chalet Alpine Cozy',
                'description': 'Chalet authentique au cœur des montagnes, parfait pour les amoureux de nature.',
                'adresse': '456 Route des Alpages',
                'ville': Ville.objects.get(nom='Chamonix'),
                'capacite_personnes': 8,
                'nombre_chambres': 4,
                'nombre_salles_bain': 2,
                'superficie': 150,
                'prix_par_nuit': Decimal('220.00'),
                'categorie': CategorieMaison.objects.get(nom='Montagne'),
                'featured': True,
                'proprietaire': proprietaire,
                'slug': 'chalet-alpine-cozy',
                'wifi': True,
                'parking': True,
                'jardin': True,
            },
            {
                'nom': 'Loft Urbain Design',
                'description': 'Loft moderne et élégant au cœur de la ville, design contemporain.',
                'adresse': '789 Rue de la République',
                'ville': Ville.objects.get(nom='Paris'),
                'capacite_personnes': 4,
                'nombre_chambres': 2,
                'nombre_salles_bain': 1,
                'superficie': 80,
                'prix_par_nuit': Decimal('150.00'),
                'categorie': CategorieMaison.objects.get(nom='Centre-ville'),
                'featured': True,
                'proprietaire': proprietaire,
                'slug': 'loft-urbain-design',
                'wifi': True,
                'climatisation': True,
            }
        ]
        
        for maison_data in maisons_data:
            maison, created = Maison.objects.get_or_create(
                slug=maison_data['slug'],
                defaults=maison_data
            )
            if created:
                self.stdout.write(f'Maison créée: {maison.nom}')

        self.stdout.write(self.style.SUCCESS('Données de test créées avec succès!'))