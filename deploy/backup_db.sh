#!/bin/bash

# Script de sauvegarde pour la base de données PostgreSQL Repavi
# Usage: ./backup_db.sh [retention_days]

set -e

# Configuration
DB_NAME="repavi"
DB_USER="repaviuser"
DB_PASSWORD="Felicien@2002"
DB_HOST="localhost"
DB_PORT="5432"

BACKUP_DIR="/root/backups/database"
RETENTION_DAYS="${1:-7}"  # Par défaut, garder 7 jours
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

# Créer le répertoire de sauvegarde
create_backup_dir() {
    log_info "Création du répertoire de sauvegarde..."
    mkdir -p "$BACKUP_DIR"
}

# Vérifier la connectivité à PostgreSQL
check_db_connection() {
    log_info "Vérification de la connexion à PostgreSQL..."
    
    export PGPASSWORD="$DB_PASSWORD"
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\q" 2>/dev/null; then
        log_info "✅ Connexion à la base de données réussie"
    else
        log_error "❌ Impossible de se connecter à la base de données"
        exit 1
    fi
    unset PGPASSWORD
}

# Sauvegarde complète de la base de données
backup_database() {
    log_info "Début de la sauvegarde de la base de données '$DB_NAME'..."
    
    local backup_file="$BACKUP_DIR/repavi_full_backup_$TIMESTAMP.sql"
    local compressed_file="$backup_file.gz"
    
    export PGPASSWORD="$DB_PASSWORD"
    
    # Sauvegarde avec pg_dump
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        --verbose \
        --clean \
        --if-exists \
        --create \
        --format=plain \
        "$DB_NAME" > "$backup_file" 2>/dev/null; then
        
        log_info "✅ Sauvegarde SQL créée: $(basename "$backup_file")"
        
        # Compression de la sauvegarde
        log_info "Compression de la sauvegarde..."
        if gzip "$backup_file"; then
            log_info "✅ Sauvegarde compressée: $(basename "$compressed_file")"
            
            # Afficher la taille du fichier
            local file_size=$(du -h "$compressed_file" | cut -f1)
            log_info "📦 Taille de la sauvegarde: $file_size"
        else
            log_warn "⚠️ Échec de la compression"
        fi
    else
        log_error "❌ Échec de la sauvegarde de la base de données"
        exit 1
    fi
    
    unset PGPASSWORD
}

# Sauvegarde du schéma uniquement
backup_schema() {
    log_info "Sauvegarde du schéma de la base de données..."
    
    local schema_file="$BACKUP_DIR/repavi_schema_$TIMESTAMP.sql"
    
    export PGPASSWORD="$DB_PASSWORD"
    
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        --schema-only \
        --verbose \
        "$DB_NAME" > "$schema_file" 2>/dev/null; then
        
        log_info "✅ Schéma sauvegardé: $(basename "$schema_file")"
        gzip "$schema_file"
    else
        log_warn "⚠️ Échec de la sauvegarde du schéma"
    fi
    
    unset PGPASSWORD
}

# Nettoyage des anciennes sauvegardes
cleanup_old_backups() {
    log_info "Nettoyage des sauvegardes de plus de $RETENTION_DAYS jours..."
    
    local deleted_files=$(find "$BACKUP_DIR" -name "repavi_*_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
    local deleted_schemas=$(find "$BACKUP_DIR" -name "repavi_schema_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
    
    local total_deleted=$((deleted_files + deleted_schemas))
    
    if [ $total_deleted -gt 0 ]; then
        log_info "🗑️ $total_deleted ancienne(s) sauvegarde(s) supprimée(s)"
    else
        log_info "📁 Aucune ancienne sauvegarde à supprimer"
    fi
}

# Afficher les statistiques de sauvegarde
show_backup_stats() {
    log_info "📊 Statistiques des sauvegardes:"
    
    local backup_count=$(find "$BACKUP_DIR" -name "repavi_*_backup_*.sql.gz" | wc -l)
    local total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "0")
    
    echo "   • Nombre de sauvegardes: $backup_count"
    echo "   • Espace total utilisé: $total_size"
    echo "   • Répertoire: $BACKUP_DIR"
    
    # Afficher les 5 dernières sauvegardes
    log_info "📋 Dernières sauvegardes:"
    find "$BACKUP_DIR" -name "repavi_*_backup_*.sql.gz" -type f -printf "%T@ %p\n" | \
        sort -n | tail -5 | while read timestamp filepath; do
        local date_str=$(date -d @"${timestamp%.*}" '+%Y-%m-%d %H:%M:%S')
        local filename=$(basename "$filepath")
        local size=$(du -h "$filepath" | cut -f1)
        echo "   • $date_str - $filename ($size)"
    done
}

# Test de restauration (dry run)
test_backup_integrity() {
    log_info "🧪 Test d'intégrité de la dernière sauvegarde..."
    
    local latest_backup=$(find "$BACKUP_DIR" -name "repavi_*_backup_*.sql.gz" -type f -printf "%T@ %p\n" | sort -n | tail -1 | cut -d' ' -f2)
    
    if [ -n "$latest_backup" ]; then
        log_info "Test du fichier: $(basename "$latest_backup")"
        
        # Test de décompression
        if zcat "$latest_backup" | head -20 | grep -q "PostgreSQL database dump"; then
            log_info "✅ Fichier de sauvegarde valide"
        else
            log_error "❌ Fichier de sauvegarde corrompu"
            return 1
        fi
    else
        log_warn "⚠️ Aucune sauvegarde trouvée pour le test"
    fi
}

# Notification en cas de problème
send_notification() {
    local status="$1"
    local message="$2"
    
    # Ici vous pouvez ajouter des notifications (email, Slack, etc.)
    if [ "$status" = "error" ]; then
        log_error "🚨 ALERTE: $message"
        # echo "$message" | mail -s "Erreur Backup Repavi" admin@repavilodges.com
    elif [ "$status" = "success" ]; then
        log_info "✅ SUCCESS: $message"
    fi
}

# Fonction principale
main() {
    log_info "🗄️ Début de la sauvegarde PostgreSQL - Repavi"
    log_info "📅 Timestamp: $TIMESTAMP"
    log_info "🕒 Rétention: $RETENTION_DAYS jours"
    
    local start_time=$(date +%s)
    
    if create_backup_dir && \
       check_db_connection && \
       backup_database && \
       backup_schema && \
       cleanup_old_backups && \
       test_backup_integrity; then
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        send_notification "success" "Sauvegarde PostgreSQL terminée avec succès en ${duration}s"
        show_backup_stats
        log_info "🎉 Sauvegarde terminée avec succès en ${duration}s"
    else
        send_notification "error" "Échec de la sauvegarde PostgreSQL"
        log_error "❌ Échec de la sauvegarde"
        exit 1
    fi
}

# Gestion des arguments
case "${1:-backup}" in
    "backup")
        main
        ;;
    "stats")
        show_backup_stats
        ;;
    "test")
        test_backup_integrity
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    *)
        echo "Usage: $0 [backup|stats|test|cleanup] [retention_days]"
        echo "  backup  - Effectue une sauvegarde complète (défaut)"
        echo "  stats   - Affiche les statistiques des sauvegardes"
        echo "  test    - Teste l'intégrité de la dernière sauvegarde"
        echo "  cleanup - Nettoie les anciennes sauvegardes"
        exit 1
        ;;
esac