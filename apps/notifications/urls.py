from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # API endpoints (pour /api/notifications/)
    path('', views.api_notifications, name='api_list'),
    path('count/', views.api_notification_count, name='api_count'),
    path('<int:pk>/read/', views.api_mark_as_read, name='api_read'),
    path('mark-all-read/', views.api_mark_all_read, name='api_mark_all'),
    
    # Pages (pour /notifications/)
    path('all/', views.all_notifications, name='all'),
]