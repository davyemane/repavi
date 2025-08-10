# ==========================================
# apps/notifications/views.py
# ==========================================
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.utils.timesince import timesince
from .models import Notification

@login_required
@require_http_methods(["GET"])
def api_notifications(request):
    """API: Liste des notifications utilisateur"""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    data = []
    for notif in notifications:
        data.append({
            'id': notif.id,
            'title': notif.title,
            'message': notif.message,
            'url': notif.url,
            'url_text': notif.url_text,
            'read': notif.read,
            'icon': notif.get_icon(),
            'color': notif.get_color(),
            'time_ago': timesince(notif.created_at),
            'actor': notif.actor.first_name if notif.actor else None,
        })
    
    unread_count = Notification.objects.filter(
        user=request.user, 
        read=False
    ).count()
    
    return JsonResponse({
        'notifications': data,
        'unread_count': unread_count
    })

@login_required 
@require_http_methods(["GET"])
def api_notification_count(request):
    """API: Compteur notifications non lues"""
    count = Notification.objects.filter(
        user=request.user,
        read=False
    ).count()
    
    return JsonResponse({'count': count})

@login_required
@require_http_methods(["POST"])
def api_mark_as_read(request, pk):
    """API: Marquer notification comme lue"""
    notification = get_object_or_404(
        Notification, 
        pk=pk, 
        user=request.user
    )
    notification.mark_as_read()
    
    return JsonResponse({'success': True})

@login_required
@require_http_methods(["POST"]) 
def api_mark_all_read(request):
    """API: Marquer toutes comme lues"""
    Notification.objects.filter(
        user=request.user,
        read=False
    ).update(read=True, read_at=timezone.now())
    
    return JsonResponse({'success': True})

@login_required
def all_notifications(request):
    """Page complète des notifications"""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Marquer comme vues
    notifications.filter(read=False).update(read=True, read_at=timezone.now())
    
    context = {
        'notifications': notifications
    }
    return render(request, 'notifications/all.html', context)