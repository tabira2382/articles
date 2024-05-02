
from django.contrib import admin
from django.urls import path
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('articles/', include('myarticles.urls')),
]
