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
import logging



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
        likes = self.request.user.likes.all()
        liked_articles = [self.get_article_details(like.article_id) for like in likes]
        context['user'] = self.request.user
        context['liked_articles'] = liked_articles
        print('liked_articles',liked_articles)
        return context
    
    def get_article_details(self, article_id):
        response = requests.get(f'https://qita.com/api/v2/items/{article_id}')
        if response.status_code == 200:
            return response.json()
        return None
    
# いいね機能
@login_required
@require_POST
def like_article(request):
    article_id = request.POST.get('article_id')
    _,created = Like.objects.get_or_create(user=request.user, article_id=article_id)
    return JsonResponse({'liked': created})