<script>
/**
 * JavaScript pour les fonctionnalités d'avis
 * À inclure dans les pages utilisant les avis
 */

// Gestion des menus d'avis
function toggleAvisMenu(avisId) {
    const menu = document.getElementById(`avis-menu-${avisId}`);
    const allMenus = document.querySelectorAll('[id^="avis-menu-"]');
    
    // Fermer tous les autres menus
    allMenus.forEach(m => {
        if (m.id !== `avis-menu-${avisId}`) {
            m.classList.add('hidden');
        }
    });
    
    // Toggle le menu cible
    menu.classList.toggle('hidden');
}

// Fermer les menus en cliquant ailleurs
document.addEventListener('click', function(event) {
    if (!event.target.closest('[onclick*="toggleAvisMenu"]')) {
        document.querySelectorAll('[id^="avis-menu-"]').forEach(menu => {
            menu.classList.add('hidden');
        });
    }
});

// Gestion des likes
function likeAvis(avisId) {
    fetch(`/avis/avis/${avisId}/like/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success !== false) {
            const likeButton = document.querySelector(`[data-avis-id="${avisId}"] .like-button`);
            const likeCount = likeButton.querySelector('.like-count');
            
            likeCount.textContent = data.nombre_likes;
            
            if (data.liked) {
                likeButton.classList.add('text-red-500');
                likeButton.classList.remove('text-gray-500');
            } else {
                likeButton.classList.add('text-gray-500');
                likeButton.classList.remove('text-red-500');
            }
            
            // Animation
            likeButton.style.transform = 'scale(1.2)';
            setTimeout(() => {
                likeButton.style.transform = 'scale(1)';
            }, 200);
        }
    })
    .catch(error => {
        console.error('Erreur like:', error);
        showNotification('Erreur lors de l\'action. Veuillez réessayer.', 'error');
    });
}

// Afficher le texte complet
function toggleFullText(avisId) {
    const card = document.querySelector(`[data-avis-id="${avisId}"]`);
    const button = card.querySelector('[onclick*="toggleFullText"]');
    
    // Ici vous pourriez faire un appel AJAX pour récupérer le texte complet
    // ou basculer entre les versions tronquée et complète
    
    if (button.textContent.includes('Lire plus')) {
        button.textContent = 'Lire moins';
        // Afficher le texte complet
    } else {
        button.textContent = 'Lire plus';
        // Afficher le texte tronqué
    }
}

// Signaler un avis
function signalerAvis(avisId) {
    // Ouvrir modal de signalement ou rediriger
    const modal = document.getElementById('signalementModal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.dataset.avisId = avisId;
    }
}

// Actions rapides de modération
function quickApprove(avisId) {
    if (confirm('Approuver cet avis ?')) {
        moderateAvis(avisId, 'approuve');
    }
}

function quickReject(avisId) {
    const raison = prompt('Raison du rejet :');
    if (raison) {
        moderateAvis(avisId, 'rejete', raison);
    }
}

function moderateAvis(avisId, statut, raison = '') {
    fetch(`/avis/avis/${avisId}/moderer/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            statut_moderation: statut,
            raison_rejet: raison
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const card = document.querySelector(`[data-avis-id="${avisId}"]`);
            if (card) {
                card.style.transition = 'all 0.3s ease';
                card.style.opacity = '0';
                card.style.transform = 'translateX(-100%)';
                
                setTimeout(() => {
                    card.remove();
                }, 300);
            }
            
            const action = statut === 'approuve' ? 'approuvé' : 'rejeté';
            showNotification(`Avis ${action} avec succès`, 'success');
        } else {
            showNotification(data.message || 'Erreur lors de la modération', 'error');
        }
    })
    .catch(error => {
        console.error('Erreur modération:', error);
        showNotification('Erreur lors de la modération', 'error');
    });
}

// Utilitaires
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function showNotification(message, type) {
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        warning: 'bg-yellow-500',
        info: 'bg-blue-500'
    };
    
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 ${colors[type]} text-white px-4 py-2 rounded-lg shadow-lg z-50 transform transition-all duration-300`;
    notification.textContent = message;
    notification.style.transform = 'translateX(100%)';
    
    document.body.appendChild(notification);
    
    // Animation d'entrée
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Animation de sortie
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les fonctionnalités d'avis
    console.log('Avis JavaScript initialized');
    
    // Auto-ajuster la hauteur des textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    });
});
</script>