# users/urls.py
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentification de base
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Vérification email
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),
    
    # Réinitialisation mot de passe
    path('password-reset-request/', views.password_reset_request_view, name='password_reset_request'),
    path('password-reset/<str:token>/', views.password_reset_view, name='password_reset'),
    
    # Profil et compte
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('account-settings/', views.account_settings_view, name='account_settings'),
    path('delete-account/', views.delete_account_view, name='delete_account'),
    
    # Dashboards
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/proprietaire/', views.dashboard_proprietaire_view, name='dashboard_proprietaire'),
    path('dashboard/locataire/', views.dashboard_locataire_view, name='dashboard_locataire'),
    
    # API/AJAX endpoints
    path('api/check-password/', views.check_password_ajax, name='check_password_ajax'),
    path('api/toggle-notification/', views.toggle_notification_ajax, name='toggle_notification_ajax'),
    path('api/user-exists/', views.user_exists_ajax, name='user_exists_ajax'),
]