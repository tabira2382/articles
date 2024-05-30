import requests
from django.core.cache import cache
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_and_cache_data():
    try:
        qiita_articles = fetch_qiita_articles()
        zenn_articles = fetch_zenn_articles()
        hatena_articles = fetch_hatena_tech_articles()
        cache.set('qiita_articles', qiita_articles, timeout=86400)  # 24時間キャッシュ
        cache.set('zenn_articles', zenn_articles, timeout=86400)
        cache.set('hatena_articles', hatena_articles, timeout=86400)
        logger.info("Data fetched and cached successfully.")
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")

def fetch_qiita_articles():
    response = requests.get('https://qiita.com/api/v2/items')
    return response.json()

def fetch_zenn_articles():
    response = requests.get('https://zenn.dev/api/articles')
    return response.json()

def fetch_hatena_tech_articles():
    response = requests.get('https://b.hatena.ne.jp/hotentry/it.rss')
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        articles = []
        for item in items:
            article = {
                'title': item.title.text,
                'link': item.link.text,
                'description': item.description.text,
            }
            articles.append(article)
        return articles
    else:
        return []

if __name__ == "__main__":
    fetch_and_cache_data()
