# utils/context_processors.py
def notifications_count(request):
    if request.user.is_authenticated:
        from apps.notifications.models import Notification
        count = Notification.objects.filter(
            user=request.user,
            read=False
        ).count()
        return {'notifications_unread_count': count}
    return {'notifications_unread_count': 0}