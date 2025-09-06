# ==========================================
# apps/facturation/context_processors.py
# ==========================================

from django.conf import settings


def facture_settings(request):
    """
    Context processor pour rendre les paramètres de facturation 
    disponibles dans tous les templates
    """
    return {
        'FACTURE_SETTINGS': getattr(settings, 'FACTURE_SETTINGS', {}),
        'PDF_SETTINGS': getattr(settings, 'PDF_SETTINGS', {}),
        'STATIC_URL': settings.STATIC_URL,
        'MEDIA_URL': settings.MEDIA_URL,
    }