# Pythonイメージをベースにする
FROM python:3.9

# MySQLクライアントライブラリをインストール
RUN apt-get update && apt-get install -y libmysqlclient-dev && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /articles

# 依存関係ファイルをコピー
COPY requirements.txt /articles/

# 依存関係をインストール
RUN pip install -r requirements.txt

# プロジェクトファイルをコピー
COPY . /articles/
