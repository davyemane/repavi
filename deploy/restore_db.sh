#!/bin/bash

# Script de restauration pour la base de données PostgreSQL Repavi
# Usage: ./restore_db.sh [backup_file.sql.gz]

set -e

# Configuration
DB_NAME="repavi"
DB_USER="repaviuser"
DB_PASSWORD="Felicien@2002"
DB_HOST="localhost"
DB_PORT="5432"

BACKUP_DIR="/root/backups/database"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Afficher les sauvegardes disponibles
list_available_backups() {
    log_info "📋 Sauvegardes disponibles:"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "Répertoire de sauvegarde inexistant: $BACKUP_DIR"
        exit 1
    fi
    
    local backups=$(find "$BACKUP_DIR" -name "repavi_*_backup_*.sql.gz" -type f -printf "%T@ %p\n" | sort -rn)
    
    if [ -z "$backups" ]; then
        log_error "Aucune sauvegarde trouvée dans $BACKUP_DIR"
        exit 1
    fi
    
    echo "$backups" | head -10 | while read timestamp filepath; do
        local date_str=$(date -d @"${timestamp%.*}" '+%Y-%m-%d %H:%M:%S')
        local filename=$(basename "$filepath")
        local size=$(du -h "$filepath" | cut -f1)
        echo "   • $date_str - $filename ($size)"
    done
}

# Sélectionner une sauvegarde
select_backup() {
    local backup_file="$1"
    
    if [ -n "$backup_file" ]; then
        # Sauvegarde spécifiée en argument
        if [ ! -f "$backup_file" ]; then
            # Essayer dans le répertoire de backup
            backup_file="$BACKUP_DIR/$backup_file"
            if [ ! -f "$backup_file" ]; then
                log_error "Fichier de sauvegarde non trouvé: $1"
                exit 1
            fi
        fi
    else
        # Utiliser la dernière sauvegarde
        backup_file=$(find "$BACKUP_DIR" -name "repavi_*_backup_*.sql.gz" -type f -printf "%T@ %p\n" | sort -rn | head -1 | cut -d' ' -f2)
        
        if [ -z "$backup_file" ]; then
            log_error "Aucune sauvegarde automatique trouvée"
            exit 1
        fi
        
        log_info "Utilisation de la dernière sauvegarde: $(basename "$backup_file")"
    fi
    
    echo "$backup_file"
}

# Vérifier la connectivité PostgreSQL
check_db_connection() {
    log_info "Vérification de la connexion PostgreSQL..."
    
    export PGPASSWORD="$DB_PASSWORD"
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "\q" 2>/dev/null; then
        log_info "✅ Connexion PostgreSQL réussie"
    else
        log_error "❌ Impossible de se connecter à PostgreSQL"
        exit 1
    fi
    unset PGPASSWORD
}

# Créer une sauvegarde de sécurité avant restauration
create_safety_backup() {
    log_info "Création d'une sauvegarde de sécurité avant restauration..."
    
    export PGPASSWORD="$DB_PASSWORD"
    local safety_backup="$BACKUP_DIR/repavi_before_restore_$TIMESTAMP.sql.gz"
    
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "$safety_backup" 2>/dev/null; then
        log_info "✅ Sauvegarde de sécurité créée: $(basename "$safety_backup")"
    else
        log_warn "⚠️ Impossible de créer la sauvegarde de sécurité"
    fi
    
    unset PGPASSWORD
}

# Arrêter les services pendant la restauration
stop_services() {
    log_info "Arrêt des services pendant la restauration..."
    
    sudo systemctl stop repavi-uvicorn || log_warn "Service repavi-uvicorn déjà arrêté"
    sleep 2
    
    log_info "✅ Services arrêtés"
}

# Redémarrer les services après restauration
start_services() {
    log_info "Redémarrage des services..."
    
    sudo systemctl start repavi-uvicorn
    sleep 5
    
    if systemctl is-active --quiet repavi-uvicorn; then
        log_info "✅ Services redémarrés"
    else
        log_error "❌ Échec du redémarrage des services"
        return 1
    fi
}

# Restaurer la base de données
restore_database() {
    local backup_file="$1"
    
    log_info "Restauration de la base de données depuis: $(basename "$backup_file")"
    
    export PGPASSWORD="$DB_PASSWORD"
    
    # Déconnecter tous les utilisateurs de la base
    log_info "Déconnexion des utilisateurs actifs..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" 2>/dev/null || true
    
    # Restauration
    log_info "Début de la restauration..."
    if zcat "$backup_file" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres 2>/dev/null; then
        log_info "✅ Base de données restaurée avec succès"
    else
        log_error "❌ Échec de la restauration"
        unset PGPASSWORD
        return 1
    fi
    
    unset PGPASSWORD
}

# Vérifier l'intégrité après restauration
verify_restoration() {
    log_info "Vérification de l'intégrité après restauration..."
    
    export PGPASSWORD="$DB_PASSWORD"
    
    # Test de connexion à la base restaurée
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\q" 2>/dev/null; then
        log_info "✅ Connexion à la base restaurée réussie"
    else
        log_error "❌ Impossible de se connecter à la base restaurée"
        unset PGPASSWORD
        return 1
    fi
    
    # Compter les tables
    local table_count=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
    
    if [ "$table_count" -gt 0 ]; then
        log_info "✅ $table_count table(s) trouvée(s) dans la base restaurée"
    else
        log_warn "⚠️ Aucune table trouvée dans la base restaurée"
    fi
    
    unset PGPASSWORD
}

# Test de l'application après restauration
test_application() {
    log_info "Test de l'application après restauration..."
    
    # Attendre que l'application soit disponible
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s http://127.0.0.1:8000 > /dev/null 2>&1; then
            log_info "✅ Application accessible après restauration"
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 2
    done
    
    log_error "❌ Application non accessible après restauration"
    return 1
}

# Confirmation utilisateur
confirm_restoration() {
    local backup_file="$1"
    
    echo
    log_warn "⚠️  ATTENTION: Cette opération va ÉCRASER la base de données actuelle !"
    echo "   Base de données: $DB_NAME"
    echo "   Sauvegarde: $(basename "$backup_file")"
    echo "   Date sauvegarde: $(date -r "$backup_file" '+%Y-%m-%d %H:%M:%S')"
    echo
    
    read -p "Êtes-vous sûr de vouloir continuer ? (tapez 'OUI' pour confirmer): " confirmation
    
    if [ "$confirmation" != "OUI" ]; then
        log_info "Restauration annulée par l'utilisateur"
        exit 0
    fi
}

# Fonction principale
main() {
    local backup_file="$1"
    
    log_info "🔄 Début de la restauration PostgreSQL - Repavi"
    
    # Afficher les sauvegardes disponibles
    list_available_backups
    echo
    
    # Sélectionner la sauvegarde
    backup_file=$(select_backup "$backup_file")
    
    # Confirmation
    confirm_restoration "$backup_file"
    
    # Processus de restauration
    local start_time=$(date +%s)
    
    if check_db_connection && \
       create_safety_backup && \
       stop_services && \
       restore_database "$backup_file" && \
       verify_restoration && \
       start_services && \
       test_application; then
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log_info "🎉 Restauration terminée avec succès en ${duration}s"
        log_info "📊 Base de données restaurée depuis: $(basename "$backup_file")"
    else
        log_error "❌ Échec de la restauration"
        log_info "🔄 Tentative de redémarrage des services..."
        start_services || true
        exit 1
    fi
}

# Gestion des arguments
case "${1:-restore}" in
    "list")
        list_available_backups
        ;;
    "restore"|*.sql.gz)
        main "$1"
        ;;
    *)
        echo "Usage: $0 [backup_file.sql.gz|list]"
        echo "  backup_file.sql.gz - Fichier de sauvegarde à restaurer"
        echo "  list              - Afficher les sauvegardes disponibles"
        echo
        echo "Si aucun fichier n'est spécifié, la dernière sauvegarde sera utilisée."
        exit 1
        ;;
esac