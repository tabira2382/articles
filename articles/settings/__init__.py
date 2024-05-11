# articles/settings/__init__.py
from .base_settings import *

# 本番環境かどうかを環境変数から判断
import os
if os.getenv('DJANGO_ENV') == 'production':
    from .prod_settings import *
else:
    try:
        from .local_settings import *
    except ImportError:
        pass
