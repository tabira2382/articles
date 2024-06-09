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

# 記事一覧API
class ArticleListAPI(APIView):
    def get(self, request, format=None):
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

# 検索API
class ArticleSearchAPI(APIView):
    def get(self, request, format=None):
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
