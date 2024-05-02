from django.shortcuts import render, redirect
from django.views import generic
import requests
from django.conf import settings


class Articles_listView(generic.TemplateView):
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