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
from django.views.generic import FormView
from .forms import SignupForm
from django.urls import reverse_lazy
from django.contrib.auth import login
from django.http import HttpResponse



class SignupView(FormView):
    template_name = 'registration/signup.html'
    form_class = SignupForm
    success_url = reverse_lazy('article_list')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)

    def form_invalid(self, form):
        # フォームが無効である場合、エラーをログに出力
        print("Form errors:", form.errors)
        return HttpResponse("Invalid form", status=400)
# 記事一覧
class Articles_listView(TemplateView):
    template_name = 'list/articles_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cached_articles = cache.get('qiita_articles')
        if cached_articles is None:
            response = requests.get('https://qiita.com/api/v2/items', params={'per_page': 20})
            if response.status_code == 200:
                articles = response.json()
                for article in articles:
                    # タグデータの抽出と整形
                    article['tag_list'] = ', '.join([tag['name'] for tag in article['tags']])
                    # データベースからいいねの数を取得
                    article['likes_count'] = Like.objects.filter(article_id=article['id']).count()
                # キャッシュに記事リストを保存
                cache.set('qiita_articles', articles, timeout=86400)
            else:
                articles = []
        else:
            articles = cached_articles
        context['articles'] = articles
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
                # キャッシュに記事データを保存（1日間キャッシュする）
                cache.set(article_id, article, timeout=86400)
            else:
                print(f"Error from API: {response.text}")
                return None
        return article



@login_required
@require_POST
def like_article(request):
    article_id = request.POST.get('article_id')
    _, created = Like.objects.get_or_create(user=request.user, article_id=article_id)
    if created:
        # キャッシュから記事を取得していいねの数を更新
        cached_article = cache.get(article_id)
        if cached_article:
            cached_article['likes_count'] = Like.objects.filter(article_id=article_id).count()
            cache.set(article_id, cached_article, timeout=86400)
            likes_count = cached_article['likes_count']
        else:
            # キャッシュになければ直接データベースからいいねの数を取得
            likes_count = Like.objects.filter(article_id=article_id).count()
        return JsonResponse({'liked': True, 'likes_count': likes_count})
    else:
        likes_count = Like.objects.filter(article_id=article_id).count()
        return JsonResponse({'liked': False, 'likes_count': likes_count})
