# Pythonイメージをベースにする
FROM python:3.9

# MySQLクライアントライブラリをインストール
RUN apt-get update && apt-get install -y libmariadb-dev-compat && rm -rf /var/lib/apt/lists/*

# lxmlライブラリをインストール
RUN apt-get update && apt-get install -y libxml2-dev libxslt-dev

# 作業ディレクトリを設定
WORKDIR /articles

# 依存関係ファイルをコピー
COPY requirements.txt /articles/

# 依存関係をインストール
RUN pip install -r requirements.txt

# プロジェクトファイルをコピー
COPY . /articles/

# サービスの起動
CMD ["db:3306", "--", "python", "manage.py", "runserver", "0.0.0.0:8000"]