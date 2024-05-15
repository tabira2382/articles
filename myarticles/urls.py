from django.urls import path
from .views import Articles_listView, ProfileView, like_article, SignupView
from .api.views import *
from .models import Like

urlpatterns = [
    path('', Articles_listView.as_view(), name='article_list'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('like/', like_article, name='like_article'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('api/articles/', ArticleListView.as_view(), name='api_articles'),
    path('api/likes/', LikeList.as_view(), name='api_likes'),
    path('api/auth/register/', RegisterAPI.as_view(), name='register'),
    path('api/auth/login/', LoginAPI.as_view(), name='login'),
]
