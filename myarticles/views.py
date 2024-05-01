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
            context['articles'] = response.json()
        else:
            context['articles'] = []
        return context