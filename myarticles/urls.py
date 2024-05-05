from django.urls import path
from .views import *

urlpatterns = [
    path('', Articles_listView.as_view(), name='article_list'),
    path('profile/', ProfileView.as_view(), name='profile'),

]
