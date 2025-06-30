#!/bin/bash

echo "🗄️ RESET COMPLET DE LA BASE DE DONNÉES REPAVI"
echo "============================================="

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Arrêter le service Django
echo -e "${YELLOW}⏹️  Arrêt du service Django...${NC}"
sudo systemctl stop repavi

# 2. Activer l'environnement virtuel
echo -e "${YELLOW}🔧 Activation de l'environnement virtuel...${NC}"
cd /root/repavi
source env/bin/activate

# 3. Sauvegarder les données importantes (optionnel)
read -p "Voulez-vous faire un dump de sauvegarde avant suppression ? (o/N): " backup_confirm
if [[ $backup_confirm == [oO] ]]; then
    echo -e "${YELLOW}💾 Création d'un backup...${NC}"
    pg_dump -h localhost -U repaviuser -d repavi > backup_$(date +%Y%m%d_%H%M%S).sql
    echo -e "${GREEN}✅ Backup créé${NC}"
fi

# 4. Supprimer tous les fichiers de migration (sauf __init__.py)
echo -e "${YELLOW}🗑️  Suppression des fichiers de migration...${NC}"
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

echo -e "${GREEN}✅ Fichiers de migration supprimés${NC}"

# 5. Supprimer et recréer la base de données PostgreSQL
echo -e "${YELLOW}🗄️  Suppression et recréation de la base de données...${NC}"

# Se connecter à PostgreSQL et supprimer/recréer la DB
sudo -u postgres psql << EOF
-- Terminer toutes les connexions à la base repavi
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'repavi';

-- Supprimer la base de données
DROP DATABASE IF EXISTS repavi;

-- Recréer la base de données
CREATE DATABASE repavi OWNER repaviuser;

-- Accorder tous les privilèges
GRANT ALL PRIVILEGES ON DATABASE repavi TO repaviuser;

\q
EOF

echo -e "${GREEN}✅ Base de données recréée${NC}"

# 6. Créer les nouvelles migrations
echo -e "${YELLOW}🔄 Création des nouvelles migrations...${NC}"

# Créer les migrations pour chaque app dans l'ordre correct
python manage.py makemigrations users
python manage.py makemigrations home
python manage.py makemigrations meubles  
python manage.py makemigrations reservations

echo -e "${GREEN}✅ Nouvelles migrations créées${NC}"

# 7. Appliquer toutes les migrations
echo -e "${YELLOW}⚡ Application des migrations...${NC}"
python manage.py migrate

echo -e "${GREEN}✅ Migrations appliquées${NC}"

# 8. Créer un superutilisateur
echo -e "${YELLOW}👤 Création du superutilisateur...${NC}"
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@repavilodges.com').exists():
    user = User.objects.create_superuser(
        email='admin@repavilodges.com',
        password='RepAvi2024!',
        first_name='Admin',
        last_name='RepAvi'
    )
    print('✅ Superutilisateur créé:')
    print('Email: admin@repavilodges.com')
    print('Password: RepAvi2024!')
else:
    print('⚠️  Un superutilisateur existe déjà')
"

# 9. Collecter les fichiers statiques
echo -e "${YELLOW}📁 Collecte des fichiers statiques...${NC}"
python manage.py collectstatic --noinput

# 10. Compiler Tailwind CSS
echo -e "${YELLOW}🎨 Compilation de Tailwind CSS...${NC}"
cd theme/static_src
if [ -f "package.json" ]; then
    npm install
    npm run build
    echo -e "${GREEN}✅ Tailwind CSS compilé${NC}"
else
    echo -e "${YELLOW}⚠️  Pas de package.json trouvé, skip Tailwind${NC}"
fi
cd ../..

# 11. Vérifier que tout est OK
echo -e "${YELLOW}🔍 Vérification finale...${NC}"
python manage.py check

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Configuration Django validée${NC}"
else
    echo -e "${RED}❌ Erreur dans la configuration Django${NC}"
    exit 1
fi

# 12. Redémarrer le service
echo -e "${YELLOW}🔄 Redémarrage du service...${NC}"
sudo systemctl start repavi
sleep 3

# 13. Vérifier le statut
echo -e "${YELLOW}📊 Vérification du statut...${NC}"
sudo systemctl status repavi --no-pager -l

# 14. Test final
echo -e "${YELLOW}🧪 Test final...${NC}"
curl -I http://localhost/ 2>/dev/null | head -3

echo ""
echo -e "${GREEN}🎉 RESET TERMINÉ AVEC SUCCÈS !${NC}"
echo ""
echo -e "${YELLOW}📝 INFORMATIONS IMPORTANTES :${NC}"
echo "   👤 Superutilisateur créé :"
echo "      Email: admin@repavilodges.com"
echo "      Password: RepAvi2024!"
echo ""
echo "   🌐 Admin: http://votre-domaine.com/admin/"
echo "   🏠 Site: http://votre-domaine.com/"
echo ""
echo -e "${YELLOW}⚠️  N'oubliez pas de changer le mot de passe admin !${NC}"

