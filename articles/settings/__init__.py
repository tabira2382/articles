# articles/settings/__init__.py
from .base_settings import *

# 本番環境かどうかを環境変数から判断
from .prod_settings import *
try:
    from .local_settings import *
except:
    pass