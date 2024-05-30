from django.apps import AppConfig
from .scheduler import start_scheduler


class MyarticlesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myarticles'

    def ready(self):
        start_scheduler()

