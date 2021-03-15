"""
Perform local login/logout on Studio

The purpose of this is to address the issue that Ironwood introduced login
redirect to the LMS, which breaks in multisite custom domain environments
"""
from django.conf import settings
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import do_logout, LoginView

urlpatterns = [
    path('logout/', auth_views.LogoutView.as_view(
         next_page=settings.LOGOUT_REDIRECT_URL), name='logout'),
    path('login', LoginView.as_view(), name='login-page'),
    path('logout2', do_logout, name='appsembler-logout'),
]
