from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
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
class LikeListAPI(APIView):
    def get(self, request, format=None):
        likes = Like.objects.all()
        serializer = LikeSerializer(likes, many=True)
        return Response(serializer.data)

# 記事一覧API
class ArticleListAPI(APIView):
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
    
#マイページ
class ProfileAPI(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        user = request.user
        likes = Like.objects.filter(user=user)
        liked_articles = [self.get_article_details(like.article_id) for like in likes]

        user_data = UserSerializer(user).data
        liked_articles_data = liked_articles

        return Response({
            'user':user_data,
            'liked_articles':liked_articles_data
        })

    def get_article_details(self, article_id):
        # キャッシュから記事データを取得
        article = cache.get(article_id)
        if not article:
            response = requests.get(f'https://qiita.com/api/v2/items/{article_id}')
            if response.status_code == 200:
                article = response.json()
                #キャッシュに記事データを保存(１日間キャッシュする)
                cache.set(article_id, article, timeout=86400)
            else:
                print(f'Error from API: {response.text}')
                return None
        return{
            'id': article['id'],
            'title': article['title'],
            'url': article['url'],
            'tag_list': ','.join([tag['name'] for tag in article['tags']]),
            'likes_count': Like.objects.filter(article_id=article_id).count()

        }
            