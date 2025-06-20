#!/bin/bash

echo "🚀 IMPLÉMENTATION COMPLÈTE DU REFACTORING REPAVI"
echo "=================================================="

# Vérification que les nouveaux modèles sont en place
echo "🔍 Vérification des modèles..."

if ! grep -q "ROLE_CHOICES" users/models.py; then
    echo "❌ ERREUR: Nouveau modèle User non trouvé dans users/models.py"
    echo "   Veuillez d'abord remplacer le contenu de users/models.py"
    exit 1
fi

if ! grep -q "gestionnaire" home/models.py; then
    echo "❌ ERREUR: Nouveau modèle Maison non trouvé dans home/models.py"
    echo "   Veuillez d'abord remplacer le contenu de home/models.py"
    exit 1
fi

echo "✅ Modèles mis à jour détectés"

# Créer les migrations
echo ""
echo "📝 Création des migrations..."
python manage.py makemigrations users
python manage.py makemigrations home

# Appliquer les migrations
echo ""
echo "🔄 Application des migrations..."
python manage.py migrate

# Configurer les permissions
echo ""
echo "🛡️ Configuration des permissions et groupes..."
python manage.py setup_permissions

# Collecter les fichiers statiques si nécessaire
echo ""
echo "📦 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput --clear

# Créer quelques données de test
echo ""
echo "🧪 Création de données de test..."

# Script Python pour créer des données de test
python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
from home.models import Ville, CategorieMaison, Maison
from users.models import ProfilClient, ProfilGestionnaire

User = get_user_model()

print("Création des données de test...")

# Créer des villes de test
ville_paris, _ = Ville.objects.get_or_create(
    nom="Paris",
    defaults={
        'code_postal': '75001',
        'departement': 'Paris',
        'pays': 'France'
    }
)

ville_lyon, _ = Ville.objects.get_or_create(
    nom="Lyon",
    defaults={
        'code_postal': '69001',
        'departement': 'Rhône',
        'pays': 'France'
    }
)

# Créer des catégories de test
cat_villa, _ = CategorieMaison.objects.get_or_create(
    nom="Villa",
    defaults={
        'description': 'Maisons avec jardin et piscine',
        'couleur': 'blue'
    }
)

cat_appartement, _ = CategorieMaison.objects.get_or_create(
    nom="Appartement",
    defaults={
        'description': 'Appartements en centre-ville',
        'couleur': 'green'
    }
)

# Créer un gestionnaire de test
if not User.objects.filter(username='gestionnaire').exists():
    gestionnaire = User.objects.create_user(
        username='gestionnaire',
        email='gestionnaire@repavi.com',
        password='test123',
        first_name='Jean',
        last_name='Dupont',
        role='GESTIONNAIRE'
    )
    
    # Créer son profil
    ProfilGestionnaire.objects.get_or_create(
        user=gestionnaire,
        defaults={
            'raison_sociale': 'Gestion Immobilière JD',
            'verifie': True
        }
    )
    print(f"✅ Gestionnaire créé: gestionnaire / test123")

# Créer un client de test
if not User.objects.filter(username='client').exists():
    client = User.objects.create_user(
        username='client',
        email='client@repavi.com',
        password='test123',
        first_name='Marie',
        last_name='Martin',
        role='CLIENT'
    )
    
    # Créer son profil
    ProfilClient.objects.get_or_create(
        user=client,
        defaults={
            'type_sejour_prefere': 'leisure'
        }
    )
    print(f"✅ Client créé: client / test123")

# Créer une maison de test
gestionnaire = User.objects.filter(role='GESTIONNAIRE').first()
if gestionnaire and not Maison.objects.filter(nom='Villa Test').exists():
    maison = Maison.objects.create(
        nom='Villa Test',
        description='Belle villa de test avec piscine',
        adresse='123 Rue de la Paix',
        ville=ville_paris,
        capacite_personnes=6,
        nombre_chambres=3,
        nombre_salles_bain=2,
        superficie=120,
        prix_par_nuit=150.00,
        disponible=True,
        featured=True,
        categorie=cat_villa,
        gestionnaire=gestionnaire,
        wifi=True,
        parking=True,
        piscine=True
    )
    print(f"✅ Maison de test créée: {maison.nom}")

print("🎯 Données de test créées avec succès!")
EOF

echo ""
echo "🎉 IMPLÉMENTATION TERMINÉE AVEC SUCCÈS!"
echo "======================================="

echo ""
echo "📋 COMPTES DE TEST CRÉÉS:"
echo "├── Super Admin: admin / admin123"
echo "├── Gestionnaire: gestionnaire / test123"
echo "└── Client: client / test123"

echo ""
echo "🌐 URLS À TESTER:"
echo "├── Admin Django: http://localhost:8000/admin/"
echo "├── Interface Gestionnaire: http://localhost:8000/repavi-admin/"
echo "├── Page d'accueil: http://localhost:8000/"
echo "└── Connexion: http://localhost:8000/users/login/"

echo ""
echo "✅ TESTS À EFFECTUER:"
echo "1. Connectez-vous avec chaque compte pour vérifier les permissions"
echo "2. Vérifiez que l'interface /repavi-admin/ fonctionne pour le gestionnaire"
echo "3. Vérifiez que les clients ne peuvent pas accéder à /repavi-admin/"
echo "4. Testez la création d'une maison avec le gestionnaire"
echo "5. Testez la création d'une réservation avec le client"

echo ""
echo "🚀 Lancement du serveur de développement..."
python manage.py runserver