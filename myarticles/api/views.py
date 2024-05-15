from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import login
from ..models import Like
from ..serializers import LikeSerializer, ArticleSerializer, UserSerializer, RegisterSerializer, LoginSerializer
from django.core.cache import cache
import requests

# ユーザー登録
class RegisterAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": token.key
        })
    
# ログイン
class LoginAPI(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": token.key
        })


# いいね取得
class LikeList(APIView):
    def get(self, request, format=None):
        likes = Like.objects.all()
        serializer = LikeSerializer(likes, many=True)
        return Response(serializer.data)

# 記事一覧API
class ArticleListView(APIView):
    def get(self, request, format=None):
        chached_articles = cache.get('qiita_articles')
        if chached_articles is None:
            response = requests.get('https://qiita.com/api/v2/items', params={'per_page': 20})
            if response.status_code == 200:
                articles = response.json()
                for article in articles:
                    article['tag_list'] = ','.join([tag['name'] for tag in article['tags']])
                    article['likes_count'] = Like.objects.filter(article_id=article['id']).count()
                cache.set('qiita_articles', articles, timeout=86400)
            else:
                articles = []
        else:
            articles = chached_articles

        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)