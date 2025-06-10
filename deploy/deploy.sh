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
    log_info "Création d'une sauvegarde..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup du code
    tar -czf "$BACKUP_DIR/repavi_code_$TIMESTAMP.tar.gz" \
        --exclude=env \
        --exclude=node_modules \
        --exclude=__pycache__ \
        --exclude=*.pyc \
        --exclude=staticfiles \
        "$PROJECT_DIR"
    
    log_info "Sauvegarde créée: repavi_code_$TIMESTAMP.tar.gz"
}

# Déploiement
deploy() {
    log_info "🚀 Déploiement en cours..."
    
    # Se placer dans le dossier projet
    cd $PROJECT_DIR || exit
    
    # Mettre à jour le code
    log_info "Mise à jour du code..."
    git pull origin $BRANCH
    
    # Activer l'environnement virtuel
    log_info "Activation de l'environnement virtuel..."
    source env/bin/activate
    
    # Installer les dépendances si besoin
    log_info "Installation des dépendances..."
    pip install -r requirements.txt
    
    # Compiler Tailwind CSS
    log_info "Compilation de Tailwind CSS..."
    npm run build
    
    # Collecter les fichiers statiques
    log_info "Collecte des fichiers statiques..."
    python manage.py collectstatic --noinput
    
    # Appliquer les migrations
    log_info "Application des migrations..."
    python manage.py migrate
    
    # Redémarrer le serveur Uvicorn
    log_info "Redémarrage du serveur..."
    pkill -f uvicorn
    sleep 2
    nohup uvicorn repavi.asgi:application --host 127.0.0.1 --port 8000 --workers 2 &
}

# Rollback en cas d'échec
rollback() {
    log_error "Échec du déploiement, rollback en cours..."
    
    # Trouver la dernière sauvegarde
    latest_backup=$(ls -t "$BACKUP_DIR"/repavi_code_*.tar.gz 2>/dev/null | head -n1)
    
    if [ -n "$latest_backup" ]; then
        log_info "Restauration depuis: $(basename $latest_backup)"
        
        # Sauvegarde du déploiement échoué
        mv "$PROJECT_DIR" "/tmp/repavi_failed_$TIMESTAMP" 2>/dev/null || true
        
        # Restauration
        mkdir -p "$PROJECT_DIR"
        tar -xzf "$latest_backup" -C "$(dirname "$PROJECT_DIR")"
        
        # Redémarrer le serveur
        cd "$PROJECT_DIR"
        source env/bin/activate
        pkill -f uvicorn
        sleep 2
        nohup uvicorn repavi.asgi:application --host 127.0.0.1 --port 8000 --workers 2 &
        
        log_info "Rollback terminé"
    else
        log_error "Aucune sauvegarde trouvée pour le rollback"
    fi
}

# Nettoyage des anciennes sauvegardes
cleanup_old_backups() {
    log_info "Nettoyage des anciennes sauvegardes (>7 jours)..."
    find "$BACKUP_DIR" -name "repavi_code_*.tar.gz" -mtime +7 -delete 2>/dev/null || true
}

# Fonction principale
main() {
    log_info "🚀 Début du déploiement de Repavi - Branche: $BRANCH"
    
    # Sauvegarde
    backup_current
    
    # Déploiement
    if deploy; then
        log_info "✅ Déploiement réussi!"
        cleanup_old_backups
    else
        log_error "❌ Déploiement échoué"
        rollback
        exit 1
    fi
    
    log_info "🎉 Déploiement terminé avec succès!"
}

# Exécution
main "$@"