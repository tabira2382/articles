from django.shortcuts import render, redirect
from django.views import generic
import requests
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Like
from django.core.cache import cache




# 記事一覧
class Articles_listView(TemplateView):
    template_name = 'list/articles_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        response = requests.get('https://qiita.com/api/v2/items', params={'per_page': 20})
        if response.status_code == 200:
            articles = response.json()
            for article in articles:
                # タグデータの抽出と整形
                article['tag_list'] = ', '.join([tag['name'] for tag in article['tags']])
            context['articles'] = articles
        else:
            context['articles'] = []
        return context
    
# マイページ
class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        likes = Like.objects.filter(user=user)
        liked_articles = [self.get_article_details(like.article_id) for like in likes]
        context['user'] = self.request.user
        context['liked_articles'] = liked_articles
        return context
    
    from django.core.cache import cache

    def get_article_details(self, article_id):
        # キャッシュから記事データを取得
        article = cache.get(article_id)
        if not article:
            response = requests.get(f'https://qiita.com/api/v2/items/{article_id}')
            if response.status_code == 200:
                article = response.json()
                # キャッシュに記事データを保存（例えば、5分間キャッシュする）
                cache.set(article_id, article, timeout=300)
            else:
                print(f"Error from API: {response.text}")
                return None
        return article



# いいね機能
@login_required
@require_POST
def like_article(request):
    article_id = request.POST.get('article_id')
    _,created = Like.objects.get_or_create(user=request.user, article_id=article_id)
    return JsonResponse({'liked': created})