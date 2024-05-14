from ..models import Like
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from ..serializers import LikeSerializer, ArticleSerializer
from django.core.cache import cache
import requests

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