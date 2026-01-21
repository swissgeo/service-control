"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from .api import api, root

urlpatterns = [
    path(settings.ROOT_PATH_PREFIX + "", root.urls),
    path(settings.API_PATH_PREFIX + "v1/", api.urls),
    # oauth2 urls are only for admin ui login
    path(settings.ADMIN_PATH_PREFIX + "", include("oauth2_proxy.urls")),
    # NOTE: the oauth_proxy endpoints needs to be registered before the admin interface endpoints
    # because they overwrite the default django admin/logout endpoints
    path(settings.ADMIN_PATH_PREFIX + "admin/", admin.site.urls),
]
