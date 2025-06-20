#!/bin/bash

echo "🔄 DÉBUT DU REFACTORING REPAVI - RESET MIGRATIONS"

# 1. Backup du code actuel
echo "📦 Sauvegarde du code actuel..."
git add .
git commit -m "Backup avant refactoring User model - Phase 1"

# 2. Arrêt du serveur de développement (si en cours)
echo "🛑 Arrêt du serveur de développement..."
pkill -f "python manage.py runserver" 2>/dev/null || true

# 3. Suppression de la base de données
echo "🗑️ Suppression de la base de données..."
rm -f db.sqlite3

# 4. Suppression de tous les fichiers de migration (sauf __init__.py)
echo "🗑️ Suppression des fichiers de migration..."
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# 5. Création des répertoires de migration s'ils n'existent pas
echo "📁 Création des répertoires de migration..."
mkdir -p home/migrations
mkdir -p users/migrations
touch home/migrations/__init__.py
touch users/migrations/__init__.py

echo "✅ Reset terminé ! Vous pouvez maintenant :"
echo "   1. Modifier le modèle User dans users/models.py"
echo "   2. Ajouter AUTH_USER_MODEL = 'users.User' dans settings.py"
echo "   3. Exécuter: python manage.py makemigrations"
echo "   4. Exécuter: python manage.py migrate"

echo "🎯 Prêt pour la Phase 1 du refactoring !"