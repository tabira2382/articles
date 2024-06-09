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
import logging

from django.core.cache import cache
from django.http import JsonResponse

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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

# データがリストか辞書かをチェックし、辞書であればリストに変換
def ensure_list(data):
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    else:
        return []
    
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
    response = requests.get('https://qiita.com/api/v2/items', params={'query': 'stocks:>100', 'per_page': 10})
    if response.status_code == 200:
        articles = response.json()
        for article in articles:
            article['tag_list'] = ','.join([tag['name'] for tag in article['tags']])
            article['article_like_count'] = article['likes_count']  # Qiita APIから直接取得
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
            article['article_like_count'] = article.get('liked_count', 0)  # Zenn APIからlikes_countを取得する場合
            article['likes_count'] = Like.objects.filter(article_id=article['id']).count()
            article['url'] = f"https://zenn.dev{article['path']}"  # 完全なURLにする
            article['image_url'] = get_og_image(article['url'])
        return articles
    return []

# はてなブックマークのテクノロジー記事を取得する関数
def fetch_hatena_tech_articles():
    response = requests.get('https://b.hatena.ne.jp/hotentry/it.rss')
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        articles = []
        for item in items:
            title = item.find('title').text if item.find('title') else None
            link = item.find('link').text if item.find('link') else None

            logger.debug(f"title: {title}")
            logger.debug(f"link: {link}")
            try:
                entry_response = requests.get(f'https://b.hatena.ne.jp/entry/jsonlite/?url={link}')
                logger.debug(f"entry_response: {entry_response}")
                if entry_response.status_code == 200:
                    entry_data = entry_response.json()
                    tags = [bookmark.get('tags', []) for bookmark in entry_data.get('bookmarks', [])]
                    flat_tags = [tag for sublist in tags for tag in sublist]  # フラットなタグリストに変換
                    unique_tags = list(set(flat_tags))  # 重複を排除
                    article_id = entry_data['eid']
                    article = {
                        'id': article_id,
                        'title': entry_data['title'],
                        'url': entry_data['url'],
                        'tag_list': ','.join(unique_tags),
                        'article_like_count': entry_data['count'],
                        'likes_count': Like.objects.filter(article_id=article_id).count(),
                        'image_url': get_og_image(link)  # OGP画像を取得
                    }
                    articles.append(article)
            except Exception as e:
                logger.debug(f"Error fetching entry data for {link}: {e}")
        logger.debug(f"Fetched {len(articles)} articles from Hatena")
        return articles
    return []


# 記事一覧API
class ArticleListAPI(APIView):
    def get(self, request, format=None):
        # キャッシュをクリア（テスト用）
        # cache.delete('qiita_articles')
        # cache.delete('zenn_articles')
        # cache.delete('hatena_articles')
        
        cached_qiita_articles = cache.get('qiita_articles')
        cached_zenn_articles = cache.get('zenn_articles')
        cached_hatena_articles = cache.get('hatena_articles')
        
        if not cached_qiita_articles or not cached_zenn_articles or not cached_hatena_articles:
            qiita_articles = fetch_qiita_articles()
            zenn_articles = fetch_zenn_articles()
            hatena_articles = fetch_hatena_tech_articles()
            articles = qiita_articles + zenn_articles + hatena_articles
            cache.set('qiita_articles', qiita_articles, timeout=86400)
            cache.set('zenn_articles', zenn_articles, timeout=86400)
            cache.set('hatena_articles', hatena_articles, timeout=86400)
        else:
            cached_qiita_articles = ensure_list(cached_qiita_articles)
            cached_zenn_articles = ensure_list(cached_zenn_articles)
            cached_hatena_articles = ensure_list(cached_hatena_articles)
            articles = cached_qiita_articles + cached_zenn_articles + cached_hatena_articles

        # 記事データをシリアライズ
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)

# 検索API
class ArticleSearchAPI(APIView):
    def get(self, request, format=None):
        # キャッシュをクリア（テスト用）
        # cache.delete('qiita_articles')
        # cache.delete('zenn_articles')
        # cache.delete('hatena_articles')
        keyword = request.query_params.get('keyword', '').lower()
        
        cached_qiita_articles = cache.get('qiita_articles')
        cached_zenn_articles = cache.get('zenn_articles')
        cached_hatena_articles = cache.get('hatena_articles')
        
        if not cached_qiita_articles or not cached_zenn_articles or not cached_hatena_articles:
            qiita_articles = fetch_qiita_articles()
            zenn_articles = fetch_zenn_articles()
            hatena_articles = fetch_hatena_tech_articles()
            articles = qiita_articles + zenn_articles + hatena_articles
            cache.set('qiita_articles', qiita_articles, timeout=86400)
            cache.set('zenn_articles', zenn_articles, timeout=86400)
            cache.set('hatena_articles', hatena_articles, timeout=86400)
        else:
            cached_qiita_articles = ensure_list(cached_qiita_articles)
            cached_zenn_articles = ensure_list(cached_zenn_articles)
            cached_hatena_articles = ensure_list(cached_hatena_articles)
            articles = cached_qiita_articles + cached_zenn_articles + cached_hatena_articles

        if keyword:
            articles = [article for article in articles if keyword in article['tag_list'].lower()]
            
        logger.debug(f"Found {len(articles)} articles matching keyword: {keyword}")

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


def get_cached_data(request):
    qiita_articles = cache.get('qiita_articles')
    zenn_articles = cache.get('zenn_articles')
    hatena_articles = cache.get('hatena_articles')
    if not qiita_articles or not zenn_articles or not hatena_articles:
        return JsonResponse({'error': 'No data available'}, status=404)
    articles = qiita_articles + zenn_articles + hatena_articles
    return JsonResponse(articles, safe=False)