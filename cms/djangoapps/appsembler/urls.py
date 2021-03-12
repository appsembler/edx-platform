"""
Perform local login/logout on Studio

The purpose of this is to address the issue that Ironwood introduced login
redirect to the LMS, which breaks in multisite custom domain environments
"""
from django.conf import settings
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import login_page, do_login, do_logout

urlpatterns = [
    path('logout/', auth_views.LogoutView.as_view(
        next_page=settings.LOGOUT_REDIRECT_URL), name='logout'),
    path('signin', login_page, name='login-page'),
    path('login', do_login, name='appsembler-login'),
    path('logout2', do_logout, name='appsembler-logout'),
]
