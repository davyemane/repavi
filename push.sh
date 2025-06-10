#!/bin/bash

# Script de push automatique pour Repavi
# Usage: ./push.sh "message de commit" [branch]

# Configuration
BRANCH="${2:-main}"
COMMIT_MESSAGE="${1}"

# Couleurs pour les logs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Vérification du message de commit
check_commit_message() {
    if [ -z "$COMMIT_MESSAGE" ]; then
        log_error "Message de commit requis!"
        echo "Usage: ./push.sh \"message de commit\" [branch]"
        echo "Exemple: ./push.sh \"Ajout nouvelle fonctionnalité\" main"
        exit 1
    fi
}

# Push automatique
push_changes() {
    log_info "🚀 Push en cours vers la branche: $BRANCH"
    
    # Vérifier s'il y a des changements
    if git diff --quiet && git diff --staged --quiet; then
        log_warn "Aucun changement à commiter"
        exit 0
    fi
    
    # Générer requirements.txt (projet Django)
    log_info "Génération du requirements.txt..."
    pip freeze > requirements.txt
    
    # Ajouter tous les fichiers
    log_info "Ajout des fichiers..."
    git add .
    
    # Afficher les fichiers modifiés
    log_info "Fichiers à commiter:"
    git diff --staged --name-only
    
    # Commit
    log_info "Commit avec le message: \"$COMMIT_MESSAGE\""
    git commit -m "$COMMIT_MESSAGE"
    
    # Pull avant push
    log_info "Pull des dernières modifications..."
    git pull origin $BRANCH
    
    # Push
    log_info "Push vers origin/$BRANCH..."
    git push origin $BRANCH
    
    log_info "✅ Push terminé avec succès!"
}

# Fonction principale
main() {
    log_info "📤 Début du push automatique"
    
    check_commit_message
    push_changes
    
    log_info "🎉 Push terminé!"
}

# Exécution
main "$@"