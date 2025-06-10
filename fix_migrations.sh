#!/bin/bash

# Script pour corriger les migrations sans supprimer la BD
set -e

echo "🔧 Correction des migrations en cours..."

# 1. Créer le dossier migrations pour users s'il n'existe pas
mkdir -p users/migrations

# 2. Créer le fichier __init__.py
touch users/migrations/__init__.py

# 3. Créer une migration fake pour users
echo "📝 Création de la migration fake users..."
cat > users/migrations/0001_initial.py << 'EOF'
from django.db import migrations

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunSQL("SELECT 1;", reverse_sql="SELECT 1;"),
    ]
EOF

# 4. Fake apply cette migration
echo "🎭 Application fake de la migration users..."
python manage.py migrate users 0001 --fake

# 5. Supprimer le fichier fake et créer la vraie migration
echo "🔄 Création de la vraie migration users..."
rm users/migrations/0001_initial.py
python manage.py makemigrations users

# 6. Appliquer la migration users
echo "✅ Application de la migration users..."
python manage.py migrate users

# 7. Créer et appliquer les migrations home
echo "🏠 Gestion des migrations home..."
python manage.py makemigrations home
python manage.py migrate home

echo "🎉 Migrations corrigées avec succès!"
echo "Vous pouvez maintenant créer un superuser avec:"
echo "python manage.py createsuperuser"