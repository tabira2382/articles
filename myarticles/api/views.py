from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.contrib.auth import login
from ..models import Like
from ..serializers import LikeSerializer, ArticleSerializer, UserSerializer, RegisterSerializer, LoginSerializer, LikeArticleSerializer
from django.core.cache import cache
import requests
from bs4 import BeautifulSoup


# OGP画像を取得する関数
def get_og_image(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image['content']:
                return og_image.get('content')
    except Exception as e:
        print(f"Error fetching OGP image: {e}")
    return None


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

# Qiitaの記事を取得する関数
def fetch_qiita_articles():
    response = requests.get('https://qiita.com/api/v2/items', params={'per_page': 20})
    if response.status_code == 200:
        articles = response.json()
        for article in articles:
            article['tag_list'] = ','.join([tag['name'] for tag in article['tags']])
            article['likes_count'] = Like.objects.filter(article_id=article['id']).count()
            article['image_url'] = get_og_image(article['url'])
        return articles
    return []

# Zennの記事を取得する関数
def fetch_zenn_articles():
    response = requests.get('https://zenn.dev/api/articles', params={'order': 'latest'})
    if response.status_code == 200:
        articles = response.json()['articles']
        for article in articles:
            tags = article.get('topics', []) or article.get('tags', [])
            article['tag_list'] = ','.join(tags)
            article['likes_count'] = 0  # Zennにはいいねの数がない場合、仮に0に設定
            article['url'] = f"https://zenn.dev{article['path']}"  # 完全なURLにする
            article['image_url'] = get_og_image(article['url'])
        return articles
    return []

# 並列実行で記事を取得する関数
def fetch_articles_parallel():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        qiita_future = executor.submit(fetch_qiita_articles)
        zenn_future = executor.submit(fetch_zenn_articles)
        qiita_articles = qiita_future.result()
        zenn_articles = zenn_future.result()
    return qiita_articles + zenn_articles

# 記事一覧API
class ArticleListAPI(APIView):
    def get(self, request, format=None):
        # cache.delete('qiita_articles')  # キャッシュのクリア
        # cache.delete('zenn_articles')  # Zennの記事用のキャッシュもクリア
        cached_qiita_articles = cache.get('qiita_articles')
        cached_zenn_articles = cache.get('zenn_articles')
        if cached_qiita_articles is None or cached_zenn_articles is None:
            qiita_articles = fetch_qiita_articles()
            zenn_articles = fetch_zenn_articles()
            articles = qiita_articles + zenn_articles
            cache.set('qiita_articles', qiita_articles, timeout=86400)
            cache.set('zenn_articles', zenn_articles, timeout=86400)
        else:
            articles = cached_qiita_articles + cached_zenn_articles

        # 記事データをシリアライズ
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

# いいね登録
class LikeArticleAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        serializer = LikeArticleSerializer(data=request.data)
        if serializer.is_valid():
            article_id = serializer.validated_data['article_id']
            _, created = Like.objects.get_or_create(user=request.user, article_id=article_id)
            if created:
                # キャッシュから記事を取得していいねの数を更新
                cached_articles = cache.get('qiita_articles')
                if cached_articles:
                    for article in cached_articles:
                        if article['id'] == article_id:
                            article['likes_count'] = Like.objects.filter(article_id=article_id).count()
                            cache.set('qiita_articles', cached_articles, timeout=86400)
                            likes_count = article['likes_count']
                            break
                else:
                    # キャッシュがない場合は直接データベースからいいねの数を取得
                    likes_count = Like.objects.filter(article_id=article_id).count()
                return Response({'liked': True, 'likes_count': likes_count}, status=status.HTTP_201_CREATED)
            else:
                likes_count = Like.objects.filter(article_id=article_id).count()
                return Response({'liked': False, 'likes_count': likes_count}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


