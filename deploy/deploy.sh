#!/bin/bash

# Script de déploiement pour Repavi
# Usage: ./deploy.sh [branch]

# Configuration
PROJECT_DIR="/var/www/repavi"
BRANCH="${1:-main}"
BACKUP_DIR="/var/backups/repavi"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Sauvegarde avant déploiement
backup_current() {
    log_info "📦 Création d'une sauvegarde..."

    mkdir -p "$BACKUP_DIR"

    tar -czf "$BACKUP_DIR/repavi_code_$TIMESTAMP.tar.gz" \
        --exclude=env \
        --exclude=node_modules \
        --exclude=__pycache__ \
        --exclude=*.pyc \
        --exclude=staticfiles \
        "$PROJECT_DIR"

    log_info "✅ Sauvegarde créée: repavi_code_$TIMESTAMP.tar.gz"
}

# Déploiement
deploy() {
    log_info "🚀 Déploiement en cours..."

    cd $PROJECT_DIR || exit

    log_info "🔄 Mise à jour du code depuis Git..."
    git pull origin $BRANCH

    log_info "⚙️ Activation de l'environnement virtuel..."
    source env/bin/activate

    log_info "📦 Installation des dépendances Python..."
    pip install -r requirements.txt

    log_info "🎨 Compilation de Tailwind CSS..."
    python manage.py tailwind build

    log_info "🧹 Nettoyage des fichiers statiques précédents..."
    rm -rf staticfiles/*

    log_info "📁 Collecte des fichiers statiques..."
    python manage.py collectstatic --noinput

    log_info "🗃️ Application des migrations..."
    python manage.py migrate

    log_info "🔁 Redémarrage du serveur Uvicorn..."
    pkill -f uvicorn
    sleep 2
    nohup uvicorn repavi.asgi:application --host 127.0.0.1 --port 8000 --workers 2 > uvicorn.log 2>&1 &
}

# Rollback en cas d'échec
rollback() {
    log_error "❌ Échec du déploiement, rollback en cours..."

    latest_backup=$(ls -t "$BACKUP_DIR"/repavi_code_*.tar.gz 2>/dev/null | head -n1)

    if [ -n "$latest_backup" ]; then
        log_info "⏪ Restauration depuis: $(basename $latest_backup)"

        mv "$PROJECT_DIR" "/tmp/repavi_failed_$TIMESTAMP" 2>/dev/null || true

        mkdir -p "$PROJECT_DIR"
        tar -xzf "$latest_backup" -C "$(dirname "$PROJECT_DIR")"

        cd "$PROJECT_DIR"
        source env/bin/activate
        pkill -f uvicorn
        sleep 2
        nohup uvicorn repavi.asgi:application --host 127.0.0.1 --port 8000 --workers 2 > uvicorn.log 2>&1 &

        log_info "✅ Rollback terminé"
    else
        log_error "⚠️ Aucune sauvegarde trouvée pour le rollback"
    fi
}

# Nettoyage des anciennes sauvegardes
cleanup_old_backups() {
    log_info "🧹 Nettoyage des sauvegardes de plus de 7 jours..."
    find "$BACKUP_DIR" -name "repavi_code_*.tar.gz" -mtime +7 -delete 2>/dev/null || true
}

# Fonction principale
main() {
    log_info "🚀 Début du déploiement de Repavi - Branche: $BRANCH"

    backup_current

    if deploy; then
        log_info "✅ Déploiement terminé avec succès !"
        cleanup_old_backups
    else
        log_error "❌ Déploiement échoué"
        rollback
        exit 1
    fi

    log_info "🎉 Déploiement terminé avec succès !"
}

# Exécution
main "$@"
