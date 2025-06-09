#!/bin/bash

# Script de déploiement pour Repavi
# Usage: ./deploy.sh [branch]

set -e  # Arrêter en cas d'erreur

# Configuration
PROJECT_DIR="/root/repavi"
VENV_DIR="$PROJECT_DIR/venv"
BRANCH="${1:-main}"
BACKUP_DIR="/root/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification des prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "Le répertoire du projet n'existe pas: $PROJECT_DIR"
        exit 1
    fi
    
    if [ ! -d "$VENV_DIR" ]; then
        log_error "L'environnement virtuel n'existe pas: $VENV_DIR"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
}

# Sauvegarde avant déploiement
backup_current() {
    log_info "Création d'une sauvegarde..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup du code
    tar -czf "$BACKUP_DIR/repavi_code_$TIMESTAMP.tar.gz" \
        --exclude=venv \
        --exclude=__pycache__ \
        --exclude=*.pyc \
        "$PROJECT_DIR"
    
    # Backup de la base de données PostgreSQL
    log_info "Sauvegarde de la base de données PostgreSQL..."
    export PGPASSWORD="Felicien@2002"
    if pg_dump -h localhost -U repaviuser -d repavi > "$BACKUP_DIR/repavi_db_$TIMESTAMP.sql" 2>/dev/null; then
        log_info "✅ Sauvegarde DB créée: repavi_db_$TIMESTAMP.sql"
    else
        log_warn "⚠️ Impossible de sauvegarder la DB PostgreSQL"
    fi
    unset PGPASSWORD
    
    log_info "Sauvegarde créée: $BACKUP_DIR/repavi_*_$TIMESTAMP.*"
}

# Test de santé avant déploiement
health_check_pre() {
    log_info "Test de santé pré-déploiement..."
    
    if ! curl -f -s http://127.0.0.1:8000 > /dev/null; then
        log_warn "L'application ne répond pas actuellement"
    else
        log_info "Application actuellement en ligne ✅"
    fi
}

# Déploiement du code
deploy_code() {
    log_info "Déploiement du code depuis la branche: $BRANCH"
    
    # Mise à jour du code
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
    
    # Activation de l'environnement virtuel
    source "$VENV_DIR/bin/activate"
    
    # Mise à jour des dépendances
    log_info "Mise à jour des dépendances..."
    pip install -r requirements.txt --quiet
    
    # Collecte des fichiers statiques
    log_info "Collecte des fichiers statiques..."
    python manage.py collectstatic --noinput
    
    # Migrations de base de données
    log_info "Application des migrations..."
    python manage.py migrate
    
    # Compilation des traductions (si applicable)
    if [ -f "locale" ]; then
        log_info "Compilation des traductions..."
        python manage.py compilemessages
    fi
}

# Redémarrage des services
restart_services() {
    log_info "Redémarrage des services..."
    
    # Redémarrage d'Uvicorn
    sudo systemctl restart repavi-uvicorn
    
    # Rechargement de Nginx
    sudo systemctl reload nginx
    
    # Attente pour que les services démarrent
    sleep 5
}

# Test de santé post-déploiement
health_check_post() {
    log_info "Test de santé post-déploiement..."
    
    # Test local
    if curl -f -s http://127.0.0.1:8000 > /dev/null; then
        log_info "✅ Application répond localement"
    else
        log_error "❌ Application ne répond pas localement"
        return 1
    fi
    
    # Test HTTPS
    if curl -f -s https://repavilodges.com > /dev/null; then
        log_info "✅ Site accessible via HTTPS"
    else
        log_error "❌ Site non accessible via HTTPS"
        return 1
    fi
    
    # Vérification des logs d'erreur récents
    if sudo journalctl -u repavi-uvicorn --since "1 minute ago" | grep -i error; then
        log_warn "⚠️ Erreurs détectées dans les logs récents"
    else
        log_info "✅ Aucune erreur dans les logs récents"
    fi
}

# Rollback en cas d'échec
rollback() {
    log_error "Échec du déploiement, rollback en cours..."
    
    # Trouver la dernière sauvegarde
    latest_backup=$(ls -t "$BACKUP_DIR"/repavi_code_*.tar.gz | head -n1)
    
    if [ -n "$latest_backup" ]; then
        log_info "Restoration depuis: $latest_backup"
        
        # Sauvegarde du déploiement échoué
        mv "$PROJECT_DIR" "/tmp/repavi_failed_$TIMESTAMP"
        
        # Restauration
        mkdir -p "$PROJECT_DIR"
        tar -xzf "$latest_backup" -C /
        
        # Redémarrage des services
        restart_services
        
        log_info "Rollback terminé"
    else
        log_error "Aucune sauvegarde trouvée pour le rollback"
    fi
}

# Nettoyage des anciennes sauvegardes
cleanup_old_backups() {
    log_info "Nettoyage des anciennes sauvegardes (>7 jours)..."
    find "$BACKUP_DIR" -name "repavi_*" -mtime +7 -delete
}

# Fonction principale
main() {
    log_info "🚀 Début du déploiement de Repavi"
    log_info "Branche: $BRANCH"
    log_info "Timestamp: $TIMESTAMP"
    
    check_prerequisites
    health_check_pre
    backup_current
    
    if deploy_code && restart_services && health_check_post; then
        log_info "✅ Déploiement réussi!"
        cleanup_old_backups
    else
        log_error "❌ Déploiement échoué"
        rollback
        exit 1
    fi
    
    log_info "🎉 Déploiement terminé avec succès!"
}

# Exécution du script principal
main "$@"