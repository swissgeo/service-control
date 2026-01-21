from django.urls import path

from oauth2_proxy.views import admin_login, admin_logout

urlpatterns = [
    path("admin/logout/", admin_logout, name="oauth2_proxy_admin_logout"),
    path("admin/oauth2/login/", admin_login, name="oauth2_proxy_admin_login"),
]
